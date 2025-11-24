def get_luck_score(pairs, places):
    luck = {}
    place_threshold = len(places) / 2
    for p1, p2 in pairs:
        if p1[1] != p2[1]:
            winner, looser = (p1[0], p2[0]) if p1[1] > p2[1] else (p2[0], p1[0])
            luck[winner] = max(0, places[winner] - place_threshold)
            luck[looser] = min(0, places[looser] - place_threshold - 1)
        else:
            score_extra_sub = 0 if places[p1[0]] > place_threshold else 1
            luck[p1[0]] = (places[p1[0]] - place_threshold - score_extra_sub) / 2
            luck[p2[0]] = (places[p1[0]] - place_threshold - score_extra_sub) / 2
    return luck
