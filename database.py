import sqlite3
import pandas
import math
df = pandas.read_excel('Players.xlsx')

def insert_new_player(player_tuple, db):
    res = True
    try:
        db.execute("INSERT INTO players VALUES " + str(player_tuple))
    except sqlite3.IntegrityError:
        res = sqlite3.IntegrityError
        print("Attempted inserting duplicate data (discord_id, character) pair already exists")
    return res

def sheetdata_to_db(line, db):
    data = [line["Discord Id"], line["Player Name"], line["Character 1"], 1, 0]
    insert_new_player(tuple(data), db)
    if not pandas.isna(line["Character 2"]):
        data[2] = line["Character 2"]
        insert_new_player(tuple(data), db)
    if not pandas.isna(line["Character 3"]):
        data[2] = line["Character 3"]
        insert_new_player(tuple(data), db)

con = sqlite3.connect("test_danisen.db")
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS players(discord_id, player_name, character, dan, points,   PRIMARY KEY (discord_id, character) )")
res = cur.execute(f"SELECT discord_id FROM players")
#id_list=res.fetchall()
#for id in id_list:
#    print(id[0])
#con.commit()

#df.apply(lambda line: sheetdata_to_db(line, cur), axis=1)