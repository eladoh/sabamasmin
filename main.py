from logging import exception
from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
import urllib.request, re, requests
from riotwatcher import LolWatcher, ApiError
import pandas as pd
from pathlib import Path

inspected_match = 0
# starting flask
app = Flask('__main__')
app.secret_key = 'hello'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SQLALCHEMY_TRaCK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(app) 

class users(db.Model):
    _id = db.Column('id', db.Integer, primary_key =True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))

    def __init__(self, name, email):
        self.name = name
        self.email = email



@app.route('/view')
def view():
    return render_template('view.html', values=users.query.all())

def all_info(name, inspected_match):
        global matches
        api_key = 'RGAPI-beb862ed-a089-43f8-b01f-9bc62df967d2' # api
        watcher = LolWatcher(api_key) # api
        my_region = 'eun1' # region

        me = watcher.summoner.by_name(my_region, name) # gets info on the summoner
        summonerLevel = me['summonerLevel'] # gets summoners lvl
        name  = me['name'] # gets summoners name

        my_ranked_stats = watcher.league.by_summoner(my_region, me['id']) # get more info on the summoner
        my_ranked_stats = my_ranked_stats[0]
                    

        wins = (my_ranked_stats['wins'])
        losses = my_ranked_stats['losses']
        rank = my_ranked_stats['tier'] 
        tier = my_ranked_stats['rank']
        rank = f'{rank} {tier}'
                        # --------------------------------------------------------
        matches = watcher.match.matchlist_by_puuid(my_region, me['puuid']) # last 20 games id 
        match_detail = watcher.match.by_id(my_region, matches[inspected_match]) # finds the match you want to inspect
        players = match_detail['info']['participants'] # get the partiocopants details


                # looping over summoners info
        participants = []
        for row in players:
            participants_row = {}
            participants_row['summoner'] = row['summonerName']
            participants_row['champion'] = row['championName']
            participants_row['kills'] = row['kills']
            participants_row['deaths'] = row['deaths']
            participants_row['assists'] = row['assists']
            kda =  row['challenges']['kda']
            kda = round(kda, 1)
            participants_row['KDA'] = kda
            participants_row['skillshotsHit'] = row['challenges']['skillshotsHit']
            participants_row['skillshotsDodged'] = row['challenges']['skillshotsDodged']
            summoner = row['summonerName']
            participants.append(participants_row)
            # sorting summoners info
        df = pd.DataFrame(participants)
        df = df.to_html()
        file = open(R'C:\Users\user1\Desktop\new_website\templates\info.html',"w", encoding='utf-8')
        file.write(df)
        file.close() 
        print('hello')
        return render_template('lol_result.html', name=name, summonerLevel=summonerLevel, rank=rank, wins=wins, losses=losses,df=df )

@app.route('/lol', methods=['POST','GET'])
def lol():
    global inspected_match
    #global name
    print(request.form)
    #name = request.form['lol']# gets users input
    try:
        if request.method == 'POST':
            if request.form['pressed'] == 'press':
                global name
                name = request.form['lol']
                return all_info(name, 0)

    #------------------------------------------------------------
    except Exception as e:
        try:
            if request.form['next'] == 'next': 
                try:
                    if inspected_match < len(matches):
                        inspected_match += 1
                    else:
                        inspected_match = 0
                    return all_info(name, inspected_match)
                except Exception as e:
                    inspected_match = 0
                    return all_info(name, inspected_match)
        except Exception as e:
            if request.form['previous'] == 'previous':
                inspected_match -= 1
                return all_info(name, inspected_match)

            
        #  flash('user not found', 'info')
        #  return redirect(url_for('lol'))
    return render_template('lol.html')



@app.route('/', methods=['POST','GET'])
def home():
    if request.method == 'POST':
        result_text = request.form['text']
        result_text = result_text.replace(' ', '+')
        html = urllib.request.urlopen(f'https://www.youtube.com/results?search_query={result_text}')
        video_ids = re.findall(r'watch\?v=(\S{11})' ,html.read().decode())
        video_ids = video_ids[0]
        print(video_ids)
        return render_template('embed.html', video_ids=video_ids)
    if request.method == 'GET':
        return render_template('index.html')
    else:
        return render_template('index.html')

def names():
    #global names
    find_name = users.query.all()
    names  = []
    for i in find_name:
        names.append(i.name)
    user = session['user']


@app.route('/login', methods=['POST', 'GET'])
def login():
    global names
    find_name = users.query.all()
    names  = []
    for i in find_name:
        names.append(i.name)
    #user = session['user']
    if request.method == 'POST': # check if we reached this page with a post request or a get request
        session.permanent = True
        email = request.form['email']
        user = request.form['nm'] # gets the input
        print(user)
        found_user = users.query.filter_by(name=user).first()
        if found_user:
            session['email'] = found_user.email
        else:
            usr = users(user, "")
            db.session.add(usr)
            db.session.commit()

        session['email'] = email
        session['user'] = user
        return redirect(url_for('user'))
    else:
       if "user"  in session:
            flash('you are already looged in')
            return redirect(url_for('user'))
    return render_template('login.html')


@app.route('/user')
def user():
    user = session['user']           
    if user in names:
        return render_template('name.html') # rendering a template
    else:
        if 'user' in session:
            email = session['email']
            found_user = users.query.filter_by(name=user).first()
            found_user.email = email
            db.session.commit()
            return render_template('user.html', user = user, email = email)
        else:
            flash('you are not logged in!')
            return redirect(url_for('login'))
            

@app.route('/logout')
def logout():
    if 'user' in session:
        email = session['email']
        user = session['user']
        session.pop('email', None)
        session.pop('user', None)
        flash(f'you have been logged out! as {user}', 'info') # flashing a message
        return redirect(url_for('login')) # redirect to a url
    else:
        flash('you must log in first')
        return redirect(url_for('login'))


# makes sure  all the data is saved and runs the website
if __name__ == '__main__':
    db.create_all()
    app.run(debug=False, host='0.0.0.0')

