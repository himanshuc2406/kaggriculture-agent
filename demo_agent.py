"""Small synthetic observation walkthrough; not a match or leaderboard result."""
import json
from main import agent

farm={'money':100,'tiles':[[None]*10 for _ in range(10)],'farmer':[0,0],
      'hands':[],'unlocked_quadrants':[0],'hires_today':0}
observation={'player':0,'day':1,'hour':0,'farms':[farm,farm],
             'market':{'prices':{}},'town':{},
             'private':{'shed':{},'seeds':{'WHEAT':1},'inventories':[{}]}}
action=agent(observation)
assert action['farmer']==['PLANT','WHEAT']
assert action['market']==[]
print(json.dumps({'scenario':'Synthetic empty-field observation',
                  'action':action,'verification':'PASS',
                  'scope':'Decision-rule smoke check only; no win-rate claim.'},indent=2))
