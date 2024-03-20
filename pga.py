#!/usr/bin/env python3
import requests
import time
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
        cutline_text = cutline_data[0].text.replace(
            'Projected Cut', '')

        cutline = get_score_as_int(cutline_text)

    rows = soup.find_all('tr', ['PlayerRow__Overview'])
    lowest_score_today = 0

    index = 0
    for row in rows:
        data = list(row.children)
        # tournament has not started
        # TODO: reimpliment this code
        if len(data) == 3:
            standing = f'{index}' # <-- this is not not technically accurate since they are all tied, but allows for easy filtering
            player = data[1].text
            score = 'E'
            today = None
            thru = data[2].text
            t_round = 0
        elif len(data) == 11:
            standing = data[1].text
            player = data[2].text
            score = data[3].text
            today = None
            thru = None
            t_round = 1
        elif len(data) > 5:
            standing = data[1].text
            player = data[3].text
            score = data[4].text
            today = data[5].text
            thru = data[6].text
            t_round = 1

        try:
            today_score = int(today)
            if today_score < lowest_score_today:
                lowest_score_today = today_score
        except:
            today_score = None

        is_cut = False
        if cutline is not None:
            score_num = get_score_as_int(score)
            if score_num > cutline:
                is_cut = True

        players.append({"tournament": tournament_title, "player": player, "standing": standing, "score": score,
                       "today": today, "today_score": today_score, "thru": thru, "hot": False, "is_cut": is_cut, "round": t_round })

        index = index + 1

    for player in players:
        if player['today_score'] is not None:
            if (player['today_score'] == lowest_score_today) or (player['today_score'] - lowest_score_today < 2):
                player['hot'] = True

    return players


def get_score_as_int(score_txt):
    """Convert score to int"""
    score_txt = score_txt.replace('+', '')
    if score_txt == 'E':
        final_score = 0

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

    table = Table(expand=True, highlight=True)
    table.add_column("⛳", justify='center')
    table.add_column(first_player['tournament'], overflow='ellipsis')
    table.add_column('Thru' if first_player['round'] > 0 else 'Tee Time', justify='right')

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
