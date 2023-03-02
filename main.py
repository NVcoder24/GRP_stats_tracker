from bs4 import BeautifulSoup
import requests
from time import sleep
from random_user_agent.user_agent import UserAgent
from datetime import datetime
import sqlite3
from flask import Flask, jsonify, request
from threading import Thread

con = sqlite3.connect("data.db", check_same_thread=False)
cur = con.cursor()
user_agent_rotator = UserAgent(limit=100)

url = "http://www.battlemetrics.com/servers/gmod?q={0}&sort=score"
proxy_api = "https://public.freeproxyapi.com/api/Proxy/ProxyByType/0/3"

LOGGING_ENABLED = False

LOG_LEVEL_LOG = 0
LOG_LEVEL_INFO = 1
LOG_LEVEL_WARNING = 2
LOG_LEVEL_ERROR = 3

log_level_to_string = {
    LOG_LEVEL_LOG:     "[LOG]    ",
    LOG_LEVEL_INFO:    "[INFO]   ",
    LOG_LEVEL_WARNING: "[WARNING]",
    LOG_LEVEL_ERROR:   "[ERROR]  ",
}

with open("logs.txt", "a") as f:
    if LOGGING_ENABLED:
        f.write(f"[START]   [{str(datetime.now())}] - LOGGING STARTED")
def log(data:str="", level:int=0):
    if LOGGING_ENABLED:
        with open("logs.txt", "a") as f:
            f.write(f"\n{log_level_to_string[level]} [{str(datetime.now())}] - {data}")

def format_str(string):
    string = str(string)
    string.replace("\n", "")
    return string

"""def get_proxies():
    att = 1
    while True:
        print(f"attempt #{att}")
        try:
            r = requests.get(url=proxy_api)
            arr = json.loads(r.content)
            ip = f'{format_str(arr["host"])}:{format_str(arr["port"])}'
            if arr["proxyLevel"] not in ["Failed", "Elite", "Transparent"]:
                print(f"proxy: {ip}; proxyLevel: {arr['proxyLevel']}")
                return ip
            else:
                print(f"failed: proxy level error\nproxyLevel: {arr['proxyLevel']}")
                return False
        except Exception as e:
            print(f"failed: general error\nERROR: {e}")
            return False"""

def get_proxies():
    log("no proxy :)", LOG_LEVEL_WARNING)
    return ""

def get_players(server_name, proxies):
    user_agent = user_agent_rotator.get_random_user_agent()
    r = requests.get(url=url.format(server_name), proxies=proxies, headers={"User-agent": user_agent})
    soup = BeautifulSoup(r.content, features="html.parser")
    all_players = soup.findAll('td', attrs={'data-title': "Players"})
    return int(all_players[0].string.split("/")[0])

def get_db_data():
    res = cur.execute("SELECT * FROM data")
    return res.fetchall()

def get_formated_db_data():
    times = []
    players = []
    for i in get_db_data():
        dt = str(datetime.fromtimestamp(i[0]).time())
        times.append(dt)
        players.append(i[1])
    return [times, players]

collect = True
def start_collecting():
    iteration = 1
    while True:
        if collect:
            log()
            log(f"===== NEW ITERATION (#{iteration}) =====", LOG_LEVEL_INFO)
            success = True
            log("getting proxy", LOG_LEVEL_INFO)
            proxies = {"http": get_proxies()}
            if proxies == False:
                success = False
                pass
            log("getting players", LOG_LEVEL_INFO)
            try:
                players = get_players("Говно", proxies)
                log(f"players: {players}", LOG_LEVEL_INFO)
            except Exception as e:
                log(f"failed to get players count: general error!\nERROR: {e}", LOG_LEVEL_ERROR)
                success = False
            
            log("writing to DB", LOG_LEVEL_INFO)
            _time = int(datetime.utcnow().timestamp())
            log(f"time: {_time}", LOG_LEVEL_INFO)
            try:
                res = cur.execute("SELECT * FROM data;")
                res = res.fetchall()
                if len(res) > 0:
                    if res[-1][1] != players:
                        cur.execute("INSERT INTO data VALUES(?, ?)", (_time, players))
                        con.commit()
                    else:
                        log("dont writing (players delta = 0)", LOG_LEVEL_WARNING)
                else:
                    cur.execute("INSERT INTO data VALUES(?, ?)", (_time, players))
                    con.commit()
            except Exception as e:
                log(f"failed to commit data into DB: general error!\nERROR: {e}", LOG_LEVEL_ERROR)
                success = False
            
            if success:
                log(f"SUCCESS! players: {players}; time: {_time}")
            else:
                log("FAILED!")
            iteration += 1
            sleep(15)
        else:
            break


app = Flask(__name__)

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ГОВНО РП СТАТЫ</title>
    </head>
    <body>
        <h1>СТАТЫ ГОВНО РП</h1>
        <a href="https://www.github.com/NVcoder24">автор этой параши</a>
        <div>
        <canvas id="myChart" style="max-width: 800px; max-height: 500px;"></canvas>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <script>
            const ctx = document.getElementById('myChart');

            async function getdata() {
                url = "/getdata"
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                });
                return response.json();
            }

            var chart = new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: [],
                                datasets: [{
                                    label: 'кол-во пидорасов',
                                    data: [],
                                    borderWidth: 1
                                }]},
                                options: {
                                    scales: {
                                        y: {
                                            beginAtZero: true
                                        }
                                    }
                                }
                            }
                        );

            function setdata() {
                getdata()
                .then((data) => {
                    chart.data.labels = data[0];
                    chart.data.datasets[0].data = data[1];
                    chart.update();
                });
            }

            function cycle_update() {
                setdata();
                setTimeout(() => {cycle_update();}, 5000);
            }
            cycle_update();
        </script>
    </body>
    </html>
    """

thr = Thread(target=start_collecting)
thr.start()

@app.route("/stopapp/")
def stopapp():
    log("stopping app...")
    global collect
    global thr
    collect = False
    thr.join()
    log("collecter thread stopped")
    request.environ.get('werkzeug.server.shutdown')
    log("werkzeug server stopped")
    log("quitting")
    quit()

@app.route("/getdata/")
def getdata():
    return jsonify(get_formated_db_data())

app.run()