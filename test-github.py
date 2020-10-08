from github import Github
from git import Repo
import json





# or using an access token
g = Github("ac7ef5dd174e79a594bf23616b3efd7570e1f047")

for repo in g.get_user().get_repos():
   print(repo.name)
  
#get settings from governance-root
#check out all observed repos
#Find all observed files
#compare with governed files
#create pull requests for changes
    #delete any existing pull requests for same file
