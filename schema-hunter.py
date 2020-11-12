import os
from github import Github
from git import Repo
import json
import tempfile
import glob
import filecmp 

config = None

gitHubToken = os.environ.get('GITHUB_TOKEN')
gitHubDomain = os.environ.get('GITHUB_DOMAIN')
schemaRepoUrl = os.environ.get('SCHEMA_REPO')

g = Github(gitHubToken)

schemaRepo = g.get_repo(schemaRepoUrl)

with open('config.json') as f:
  config = json.load(f)

def huntRepo(repo):
  with tempfile.TemporaryDirectory() as workingDir:
       
      Clone(workingDir,"source", repo["url"],repo["branch"])

      existingPullRequest = FindPullRequest(repo, schemaRepo)

      if(existingPullRequest is None):
        #compare to main branch and create branch and pull request only if found changes

        print('comparing to main branch')
        
        Clone(workingDir, "governance", schemaRepoUrl, "main")

      else:
        print("comparing to existing branch:" + str(existingPullRequest.head.ref))

        Clone(workingDir, "governance", schemaRepoUrl, existingPullRequest.head.ref)

      mappings = GetFileMappings(workingDir + "/source", workingDir + "/governance", repo)

      print(mappings)

      changes = CalculateChanges(mappings)

      for cng in changes:
        print(cng)
      #files = glob.glob(workingDir + '/**/*.*', recursive=True)

      #print(files)
      #repo_schema.create_pull(title=("[" +  repo["name"]+ "]"), body= "test", head="Risk-1111202",base="main")

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

def GetFileMappings(source, dest, repo):
  mappings=[]
  for fs in repo["fileSets"]:
    sourceFiles = glob.glob(source + fs["source"], recursive=True)
    for sf in sourceFiles:
      mapping = dict(source=sf, destination=(dest + fs["dest"]+ "/" + os.path.basename(sf)))
      mappings.append(mapping)
  return mappings

def Clone(workDir, name, url, branch):
  cloneUrl="https://" + gitHubToken +"@" + gitHubDomain + "/" + url     
  return Repo.clone_from(url = cloneUrl, to_path = workDir  + "/" + name,branch=branch)

def FindPullRequest(repo, repo_schema):
  targetPullRequest = None
  for p in repo_schema.get_pulls(state='open', base='main'):
    if( IsPullOurPullRequest(repo,p)):
      targetPullRequest=p
      break
  return targetPullRequest
    
def IsPullOurPullRequest(repo, pr):
  if(str.startswith(pr.title, ("[" +  repo["name"]+ "]"))):
    return True
  else:
    return False
    

for tRepo in config["trackedRepos"]:
  huntRepo(tRepo)

