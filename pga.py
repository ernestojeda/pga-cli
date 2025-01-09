#!/usr/bin/env python3
import requests
import time
import re
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from rich.live import Live
from rich.table import Table

def get_player_data():
    """Get player data from ESPN"""
    players=[]
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    html = requests.get("https://www.espn.com/golf/leaderboard", headers=headers).text
    soup = BeautifulSoup(html, features="html.parser")

    tournament_title = soup.find('h1', ['Leaderboard__Event__Title']).text

    cutline_row = soup.find_all('tr', ['cutline'])
    cutline = None
    if cutline_row:
        cutline_data = list(cutline_row[0].children)
        cutline_text = cutline_data[0].text.replace('Projected Cut', '')
        cutline = get_as_int(cutline_text)

    rows = soup.find_all('tr', ['PlayerRow__Overview'])
    lowest_score_today = 0

    # Need to see what happens here before tournament starts
    current_round_raw = soup.find_all('div', ['status'])[0].text
    current_round_html = re.match("Round (\\d*).*", current_round_raw)

    # round 5 is tournament over
    current_round_text = '5' if current_round_html is None else current_round_html.group(1)

    current_round = 0 if get_as_int(current_round_text) is None else get_as_int(current_round_text)

    round_indeces = {
        0: {
            'player': 1,
            'thru': 2,
        },
        1: {
            'standing': 1,
            'player': 2,
            'score': 3,
            'today': 4,
            'thru': 5,
        },
        2: {
            'standing': 1,
            'player': 3,
            'score': 4,
            'today': 5,
            'thru': 6,
        },
        3: {
            'standing': 1,
            'player': 3,
            'score': 4,
            'today': 5,
            'thru': 6,
        },
        4: {
            'standing': 1,
            'player': 3,
            'score': 4,
            'today': 5,
            'thru': 6,
        },
        5: {
            'standing': 1,
            'player': 2,
            'score': 3,
            'today': 7,
            'thru': 9,
        },
    }

    index = 0
    indeces = round_indeces[current_round]
    for row in rows:
        data = list(row.children)
        # Round not started, need to make up certain values
        if len(data) == 3:
            standing = f'{index}' # <-- this is not not technically accurate since they are all tied, but allows for easy filtering
            player = data[1].text
            score = 'E'
            today = None
            thru = data[2].text
        elif len(data) > 5:
            standing = data[indeces['standing']].text
            player = data[indeces['player']].text
            score = data[indeces['score']].text
            today = data[indeces['today']].text
            thru = data[indeces['thru']].text
        try:
            today_score = int(today)
            if today_score < lowest_score_today:
                lowest_score_today = today_score
        except:
            today_score = None

        is_cut = False
        if cutline is not None and score != 'WD':
            score_num = get_as_int(score)
            if score_num > cutline:
                is_cut = True

        players.append({"tournament": tournament_title, "player": player, "standing": standing, "score": score,
                       "today": today, "today_score": today_score, "thru": thru, "hot": False, "is_cut": is_cut, "round": current_round})

        index = index + 1

    for player in players:
        if current_round < 5:
            thru = '18' if player['thru'] == 'F' else player['thru']
            if '*' in thru:
                thru = thru.replace('*', '')

            if player['today_score'] is not None:
                if (player['today_score'] == lowest_score_today) or (player['today_score'] - lowest_score_today < 3):
                    player['hot'] = True
                elif (player['today_score'] < 0 and 'M' not in player['thru'] and player['today_score'] + int(thru) <= 2):
                    player['hot'] = True

    return players


def get_as_int(score_txt):
    """Convert score to int"""
    score_txt = score_txt.replace('+', '')
    if score_txt == 'E':
        return 0

    try:
        final_score = int(score_txt)
    except:
        final_score = None
        pass

    return final_score


def generate_table(args) -> Table:
    """Make a new table."""
    players = get_player_data()

    first_player = players[0]

    last_col_label = 'Thru'

    if first_player['round'] == 0:
        last_col_label = 'Tee Time'
    elif first_player['round'] == 5:
        last_col_label = 'Earnings'

    table = Table(expand=True, highlight=True)
    table.add_column("⛳", justify='center')
    table.add_column(first_player['tournament'], overflow='ellipsis')
    table.add_column(last_col_label, justify='right')

    cutline_added = False
    for player in players:
        standing = player['standing']
        if standing is not None:
            try:
                standing = int(standing.replace('T', '').replace('-', ''))
            except:
                standing = 1000

        if (standing is None and args.top is None) or standing <= args.top:
            if player['is_cut'] and not cutline_added:
                table.add_row(
                    '', '✂️  -----------------------', ''
                )
                cutline_added = True

            score_color = 'white'
            if '-' in player['score']:
                score_color = 'red'
            elif player['score'] == 'E':
                score_color = 'green'

            player_name = player['player']
            if player['hot']:
                player_name = f"{player_name} 🔥"
                try:
                    thru_hole = int(player['thru'])
                    leader_thru = int(players[0]['thru'])
                    if thru_hole < leader_thru:
                        player_name = f"[u]{player_name}[/u]"
                except:
                    pass

            if player['thru'] == 'F':
                player_name = f"[rgb(150,150,150)]{player_name}"

            if player['is_cut']:
                player_name = f"[strike]{player_name}[/strike]"

            player_text = f"{player_name}"
            if player['today'] is not None:
                player_text += f" ({player['today']})"

            table.add_row(
                f"[{score_color}]{player['score']}", player_text, player['thru']
            )
    return table


def get_parser():
    """ setup parser and return parsed command line arguments
    """
    parser = ArgumentParser(
        description='PGA leaderboard from ESPN now in your terminal')
    parser.add_argument(
        '--top',
        type=int,
        required=False,
        default=1000,
        help='Top [n] players to show')

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    with Live(generate_table(args), refresh_per_second=1) as live:
        while True:
            time.sleep(30)
            live.update(generate_table(args))


if __name__ == '__main__':
    main()
