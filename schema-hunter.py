import os
from github import Github
from git import Repo
import json
import tempfile
import glob
import filecmp 
from shutil import copy
import time
import urllib.request


config = None

gitHubToken = os.environ.get('GIT_HUB_TOKEN')
gitHubDomain = os.environ.get('GIT_HUB_DOMAIN')
schemaRepoUrl = os.environ.get('SCHEMA_REPO')

g = Github(gitHubToken) #gihub api root object

schemaRepo = g.get_repo(schemaRepoUrl) #reference to remote schemarepo

config = json.loads(urllib.request.urlopen(os.environ.get('CONFIG_URL')).read()) #load configuration file

def HuntRepo(repo):
  with tempfile.TemporaryDirectory() as workingDir: #create a temporary working folder to do checkouts
      
      print(repo["name"] + ":cloning source from: " +  repo["url"])
             
      Clone(workingDir,"source", repo["url"],repo["branch"]) #clone github repo being "hunted"

      existingPullRequest = FindPullRequest(repo, schemaRepo) #check if there is a pull request in governance repo from this repo 

      if(existingPullRequest is None):

        print(repo["name"] + ":comparing to main branch")
        
        Clone(workingDir, "governance", schemaRepoUrl, "main")

      else:
        print(repo["name"] + ":comparing to existing branch:" + str(existingPullRequest.head.ref))

        Clone(workingDir, "governance", schemaRepoUrl, existingPullRequest.head.ref)

      mappings = GetFileMappings(workingDir + "/source", workingDir + "/governance", repo)

      changes = CalculateChanges(mappings)

      if changes:
         
        print(repo["name"] + ":found changes: " + str(changes.count))

        if(existingPullRequest is None): #adding changes to new branch/pull request

          schemaLocalRepo = Repo(workingDir + "/governance")

          bName=repo["name"] + '-' + str(int(time.time()))
          
          current = schemaLocalRepo.create_head(bName)

          current.checkout()   

          ApplyChanges(changes)
 
          schemaLocalRepo.git.add(A=True)
          schemaLocalRepo.git.commit(m='Schema changes from ' + repo["name"])
          schemaLocalRepo.git.push('--set-upstream', 'origin', current)

          schemaRepo.create_pull(title=("[" +  repo["name"]+ "] Schema Changes"), body= ("Changes to schema files were detected in " + repo["url"] + " branch=" + repo["branch"]), head=bName,base="main")
        else: # adding changes to existing branch/pull request
          ApplyChanges(changes)
          schemaLocalRepo = Repo(workingDir + "/governance")
          schemaLocalRepo.git.add(A=True)
          schemaLocalRepo.git.commit(m='Schema changes from ' + repo["name"])
          schemaLocalRepo.git.push()
      else:
        print(repo["name"] + ":no changes")

#copies files from cloned source repo to cloned governance repo BRANCH
def ApplyChanges(changes):
  for c in changes:
    dstfolder = os.path.dirname(c["mapping"]["destination"])
    if not os.path.exists(dstfolder):
      os.makedirs(dstfolder)
    copy(c["mapping"]["source"], c["mapping"]["destination"])

#compares files pointed to by mappings
def CalculateChanges(mappings):
  changes = []
  for m in mappings:
    if(os.path.exists(m["destination"])):
      if(filecmp.cmp(m["source"], m["destination"])):
        pass
      else:
        changes.append(dict(mapping=m, changeType='change'))
    else:
      changes.append(dict(mapping=m, changeType='add'))
  return changes

#locates files in cloned out source repo according to Unix file system expansion rules and maps them to files in governance cloned repo
def GetFileMappings(source, dest, repo):
  mappings=[]
  for fs in repo["fileSets"]:
    sourceFiles = glob.glob(source + fs["source"], recursive=True)
    for sf in sourceFiles:
      mapping = dict(source=sf, destination=(dest + fs["dest"]+ "/" + os.path.basename(sf)))
      mappings.append(mapping)
  return mappings

#clones git repo branch into a specified path using a given token
def Clone(workDir, name, url, branch):
  cloneUrl="https://" + gitHubToken +"@" + gitHubDomain + "/" + url     
  return Repo.clone_from(url = cloneUrl, to_path = workDir  + "/" + name,branch=branch)

#locates an existing pullrequest from a give source repo
def FindPullRequest(repo, repo_schema):
  targetPullRequest = None
  for p in repo_schema.get_pulls(state='open', base='main'):
    if( IsOwnedPullRequest(repo,p)):
      targetPullRequest=p
      break
  return targetPullRequest
    
#checks if a given pull request is for a given source repo   
def IsOwnedPullRequest(repo, pr):
  if(str.startswith(pr.title, ("[" +  repo["name"]+ "]"))):
    return True
  else:
    return False
    
errorCount = 0

for tRepo in config["trackedRepos"]: #hunt each repo in configuration file one-by-one
  try:
    print("starting to process " + tRepo["name"])
    HuntRepo(tRepo)
  except Exception as e:
    print ( tRepo["name"] + ':' + e.__doc__)
    print ( tRepo["name"] + ':' + e.message)
    errorCount=errorCount+1

if errorCount > 0:
  raise Exception("Errors were encountered while processing. Not all repos were checked. See above for details")
