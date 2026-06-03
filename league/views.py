# league/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django import forms
from .models import Team, Player, Match, Goal, Card

# --- Model Forms for Custom Admin Interface ---
class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'logo', 'home_ground']

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'team', 'position', 'jersey_number']
        
class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_team', 'away_team', 'match_date', 'status']
        widgets = {
            'match_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full border border-gray-300 p-2 rounded text-sm bg-white'}),
            'home_team': forms.Select(attrs={'class': 'w-full border border-gray-300 p-2 rounded text-sm bg-white'}),
            'away_team': forms.Select(attrs={'class': 'w-full border border-gray-300 p-2 rounded text-sm bg-white'}),
            'status': forms.Select(attrs={'class': 'w-full border border-gray-300 p-2 rounded text-sm bg-white'}),
        }
        
from django import forms
from .models import Team, Player

class TeamEditForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'logo', 'home_ground']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium'}),
            'home_ground': forms.TextInput(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium'}),
        }
from django import forms
from .models import Player

class PlayerEditForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'team', 'position', 'jersey_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition'}),
            'team': forms.Select(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition'}),
            'position': forms.Select(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition'}),
            'jersey_number': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 p-2.5 rounded-xl text-sm bg-white font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition'}),
        }

# ==========================================
# PUBLIC VIEWS (User Facing Side)
# ==========================================


def vfl_admin_required(view_func):
    """Custom decorator that bypasses Django auth tables and relies on code-level sessions."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_vfl_admin'):
            return redirect('custom_admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# --- NEW: Custom Hardcoded Login/Logout Views ---
def custom_admin_login(request):
    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")
        
        if username_input == "vflmanager" and password_input == "VflLeague2026!":
            request.session['is_vfl_admin'] = True
            request.session.modified = True
            return redirect('admin_dashboard')  # Redirects to your existing path/name
        else:
            messages.error(request, "Invalid Administrative Credentials.")
            
    return render(request, 'custom_admin/login.html')

def custom_admin_logout(request):
    if 'is_vfl_admin' in request.session:
        del request.session['is_vfl_admin']
    return redirect('custom_admin_login')


def standings_table(request):
    teams = Team.objects.all()
    table_data = []
    for team in teams:
        data = team.statistics
        data['team'] = team
        table_data.append(data)
    
    # Sort: Points -> Goal Difference -> Goals For
    sorted_table = sorted(table_data, key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
    
    # --- NEW: Fetch Fixtures for the User Frontend ---
    # 1. Upcoming Matches: Status is Scheduled, ordered oldest to newest
    upcoming_matches = Match.objects.filter(status='Scheduled').order_by('match_date')
    
    # 2. Match Results: Status is Played, ordered latest to oldest
    match_results = Match.objects.filter(status='Played').order_by('-match_date')

    context = {
        'table': sorted_table,
        'upcoming_matches': upcoming_matches,
        'match_results': match_results,
    }
    return render(request, 'league/standings.html', context)


def top_scorers(request):
    scorers = Player.objects.annotate(total_goals=Count('scored_goals')).filter(total_goals__gt=0).order_by('-total_goals')
    return render(request, 'league/top_scorers.html', {'scorers': scorers})


def clean_sheets_leaderboard(request):
    teams = Team.objects.all()
    leaderboard = []
    
    for team in teams:
        # 1. Pull the team's dynamic clean sheets count
        cs_count = team.statistics['cs']
        
        # 2. Grab the goalkeeper(s) assigned to this specific team
        # Using .first() handles cases where a team has one clear starter.
        keeper = team.players.filter(position='GK').first()
        
        # 3. Fallback name if a team doesn't have a goalkeeper assigned in the DB yet
        keeper_name = keeper.name if keeper else "No Active Goalkeeper"
        
        leaderboard.append({
            'keeper_name': keeper_name,
            'club_name': team.name,
            'clean_sheets': cs_count
        })
        
    # Sort the list by clean sheets descending
    sorted_leaderboard = sorted(leaderboard, key=lambda x: -x['clean_sheets'])
    
    return render(request, 'league/clean_sheets.html', {'leaderboard': sorted_leaderboard})


# ==========================================
# CUSTOM ADMIN PORTAL VIEWS
# ==========================================
@vfl_admin_required
def admin_dashboard(request):
    """Central control panel for creating teams, players, matches, and viewing fixtures."""
    teams = Team.objects.all()
    players = Player.objects.all()
    matches = Match.objects.all().order_by('-match_date')
    
    # Initialize forms for presentation
    team_form = TeamForm()
    player_form = PlayerForm()
    match_form = MatchForm()
    
    if request.method == 'POST':
        if 'submit_team' in request.POST:
            form = TeamForm(request.POST, request.FILES)
            if form.is_valid(): 
                form.save()
            return redirect('admin_dashboard')
            
        elif 'submit_player' in request.POST:
            form = PlayerForm(request.POST)
            if form.is_valid(): 
                form.save()
            return redirect('admin_dashboard')
            
        elif 'submit_match' in request.POST:
            form = MatchForm(request.POST)
            if form.is_valid():
                form.save()
            return redirect('admin_dashboard')

    context = {
        'teams': teams,
        'players': players,
        'matches': matches,
        'team_form': team_form,
        'player_form': player_form,
        'match_form': match_form, # Injected to display on template frontend
    }
    return render(request, 'league/admin_dashboard.html', context)

@vfl_admin_required
def manage_match_events(request, match_id):
    """The central Match Console room allowing infinite updates and removals."""
    match = get_object_or_404(Match, id=match_id)
    
    if request.method == 'POST':
        # 1. Update overall match scores and layout status
        if 'update_match' in request.POST:
            match.home_score = int(request.POST.get('home_score', 0))
            match.away_score = int(request.POST.get('away_score', 0))
            match.status = request.POST.get('status', 'Scheduled')
            match.save()
            return redirect('manage_match_events', match_id=match.id)
            
        # 2. Add New Goal Timeline Element
        elif 'add_goal' in request.POST:
            player_id = request.POST.get('player')
            player = get_object_or_404(Player, id=player_id)
            Goal.objects.create(
                match=match,
                team=player.team,
                player=player,
                minute=request.POST.get('minute')
            )
            return redirect('manage_match_events', match_id=match.id)

        # 3. Add New Card Discipline Element
        elif 'add_card' in request.POST:
            player_id = request.POST.get('player')
            player = get_object_or_404(Player, id=player_id)
            Card.objects.create(
                match=match,
                player=player,
                card_type=request.POST.get('card_type'),
                minute=request.POST.get('minute')
            )
            return redirect('manage_match_events', match_id=match.id)
            
        # 4. DELETE an existing Goal Event completely
        elif 'delete_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal_to_del = get_object_or_404(Goal, id=goal_id, match=match)
            goal_to_del.delete()
            return redirect('manage_match_events', match_id=match.id)

        # 5. DELETE an existing Card Event completely
        elif 'delete_card' in request.POST:
            card_id = request.POST.get('card_id')
            card_to_del = get_object_or_404(Card, id=card_id, match=match)
            card_to_del.delete()
            return redirect('manage_match_events', match_id=match.id)

    competing_players = Player.objects.filter(team__in=[match.home_team, match.away_team])
    
    context = {
        'match': match,
        'goals': match.goals.all().order_by('minute'),
        'cards': match.cards.all().order_by('minute'),
        'players': competing_players,
    }
    return render(request, 'league/match_detail_admin.html', context)


# ==========================================
# ROSTER VIEW & DATA EDITING LOGIC
# ==========================================

@vfl_admin_required
def manage_rosters(request):
    """Lists all teams pre-mapped with their relational nested player querysets."""
    teams = Team.objects.all().prefetch_related('players')
    return render(request, 'league/manage_rosters.html', {'teams': teams})


@vfl_admin_required
def edit_team(request, team_id):
    """Fetches a specific team object instance and overrides its file/string variables."""
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        form = TeamEditForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            return redirect('manage_rosters')
    else:
        form = TeamEditForm(instance=team)
    return render(request, 'league/edit_team.html', {'form': form, 'team': team})


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages # Optional: for user feedback

@vfl_admin_required
def edit_player(request, player_id):
    """Fetches a specific player object instance and updates their team or position values."""
    player = get_object_or_404(Player, id=player_id)
    
    if request.method == 'POST':
        # Bind the incoming POST data to the existing player instance
        form = PlayerEditForm(request.POST, instance=player)
        if form.is_valid():
            form.save()
            # Optional: messages.success(request, f"{player.name}'s profile updated successfully!")
            return redirect('manage_rosters')
    else:
        # GET request: Instantiate the form with the player's existing data
        form = PlayerEditForm(instance=player)
        
    return render(request, 'league/edit_player.html', {
        'form': form, 
        'player': player
    })


# league/views.py

def disciplinary_board(request):
    """Publicly accessible lookup board exposing active player suspension indicators."""
    all_players = Player.objects.all().select_related('team')
    
    tracked_players = []
    for player in all_players:
        status = player.disciplinary_status
        # Only show players who have at least one warning count or an active suspension
        if status['yellow_count'] > 0 or status['is_suspended']:
            tracked_players.append({
                'player': player,
                'yellows': status['yellow_count'],
                'suspended': status['is_suspended'],
                'reason': status['reason']
            })
            
    # Sort: Put suspended players at the top, then sort by yellow card count
    sorted_board = sorted(tracked_players, key=lambda x: (-int(x['suspended']), -x['yellows']))
    
    return render(request, 'league/disciplinary_board.html', {'board': sorted_board})