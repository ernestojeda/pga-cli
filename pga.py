#!/usr/bin/env python3
import requests
import time
import os
from bs4 import BeautifulSoup
from rich.live import Live
from rich.table import Table

def get_player_data():
    """Get player data from ESPN"""
    players=[]
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    html = requests.get("https://www.espn.com/golf/leaderboard", headers=headers).text
    soup = BeautifulSoup(html, features="html.parser")

    cutline_row = soup.find_all('tr', ['cutline'])
    cutline = None
    if cutline_row:
        cutline_data = list(cutline_row[0].children)
        cutline_text = cutline_data[0].text.replace(
            'Projected Cut', '')

        cutline = get_score_as_int(cutline_text)

    rows = soup.find_all('tr', ['PlayerRow__Overview'])
    lowest_score_today = 0
    
    for row in rows:
        data = list(row.children)
        standing = data[1].text
        player = data[3].text
        score = data[4].text
        today = data[5].text
        thru = data[6].text

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

        players.append({ "player": player, "standing": standing, "score": score, "today": today, "today_score": today_score, "thru": thru, "hot": False, "is_cut": is_cut })

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
        pass

    return final_score


def generate_table() -> Table:
    """Make a new table."""
    table = Table(width=os.get_terminal_size().columns)
    table.add_column("⛳", justify='center')
    table.add_column("Player")
    table.add_column("Thru", justify="right")

    players = get_player_data()
    cutline_added = False
    for player in players:
        if player['is_cut'] and not cutline_added:
            table.add_row(
                "", "✂️  -----------------------", ""
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

        table.add_row(
            f"[{score_color}]{player['score']}", f"{player_name} ({player['today']})", player['thru']
        )
    return table

def main():
    with Live(generate_table(), refresh_per_second=1) as live:
        while True:
            time.sleep(30)
            live.update(generate_table())


if __name__ == '__main__':
    main()
