from django.db import models
from django.db.models import Q

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    home_ground = models.CharField(max_length=150)

    def __str__(self):
        return self.name

    @property
    def statistics(self):
        """Dynamically computes league standings statistics for this team."""
        stats = {'mp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0, 'cs': 0}
        
        # Fetch all completed matches involving this team
        matches = Match.objects.filter(
            Q(home_team=self) | Q(away_team=self), 
            status='Played'
        )
        
        stats['mp'] = matches.count()
        
        for match in matches:
            if match.home_team == self:
                stats['gf'] += match.home_score
                stats['ga'] += match.away_score
                if match.away_score == 0:
                    stats['cs'] += 1
                
                if match.home_score > match.away_score:
                    stats['w'] += 1
                    stats['pts'] += 3
                elif match.home_score == match.away_score:
                    stats['d'] += 1
                    stats['pts'] += 1
                else:
                    stats['l'] += 1
            else:
                stats['gf'] += match.away_score
                stats['ga'] += match.home_score
                if match.home_score == 0:
                    stats['cs'] += 1
                
                if match.away_score > match.home_score:
                    stats['w'] += 1
                    stats['pts'] += 3
                elif match.away_score == match.home_score:
                    stats['d'] += 1
                    stats['pts'] += 1
                else:
                    stats['l'] += 1
                    
        stats['gd'] = stats['gf'] - stats['ga']
        return stats


class Player(models.Model):
    POSITIONS = [
        ('GK', 'Goalkeeper'),
        ('DF', 'Defender'),
        ('MF', 'Midfielder'),
        ('FW', 'Forward'),
    ]
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=2, choices=POSITIONS)
    jersey_number = models.PositiveIntegerField()

    class Meta:
        unique_together = ('team', 'jersey_number')

    def __str__(self):
        return f"{self.name} ({self.team.name})"
    
    # FIXED: This property is now correctly nested inside the Player model class block
    @property
    def disciplinary_status(self):
        """
        Computes dynamic tournament suspension variables based on specific criteria:
        - 2 Yellows in 1 single match -> 1 Match Suspension & counts reset.
        - 3 Yellows total within regular league fixtures -> 1 Match Suspension.
        - Post-league (Knockout/Semi-finals) -> Counts reset to 0.
        """
        from .models import Card
        
        # 1. Fetch card logs linked to this player, ordered chronologically
        all_cards = Card.objects.filter(player=self).select_related('match').order_by('match__match_date')
        
        yellow_count = 0
        is_suspended = False
        reason = ""
        
        # Track single match metrics to find immediate double yellow dismissals
        match_card_registry = {}
        
        for card in all_cards:
            # Check if match is part of the knockout stage (e.g., Semi-finals)
            if "semi" in card.match.status.lower():
                continue
                
            if card.card_type == 'Yellow':
                yellow_count += 1
                
                # Map items to cross-reference single game counters
                match_id = card.match.id
                match_card_registry[match_id] = match_card_registry.get(match_id, 0) + 1
                
                # CRITERIA B: 2 Yellows received inside ONE matching fixture instance
                if match_card_registry[match_id] == 2:
                    is_suspended = True
                    reason = "Indirect Red Card (2 Yellows in 1 Match)"
                    yellow_count = 0 
                    break

        # CRITERIA A: Accumulating 3 independent yellow infractions across general tournament matches
        if yellow_count >= 3 and not is_suspended:
            is_suspended = True
            reason = "Accumulated 3 Yellow Cards"

        return {
            'yellow_count': yellow_count,
            'is_suspended': is_suspended,
            'reason': reason
        }


class Match(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Played', 'Played'),
    ]
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    match_date = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Scheduled')
    home_score = models.PositiveIntegerField(default=0)
    away_score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} on {self.match_date.strftime('%Y-%m-%d')}"


class Goal(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='goals')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='scored_goals')
    minute = models.PositiveIntegerField()

    def __str__(self):
        return f"Goal by {self.player.name} ({self.minute}')"


class Card(models.Model):
    CARD_TYPES = [
        ('Yellow', 'Yellow'),
        ('Red', 'Red'),
    ]
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='cards')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='received_cards')
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    minute = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.card_type} Card to {self.player.name} ({self.minute}')"