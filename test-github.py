from github import Github



# or using an access token
g = Github("ac7ef5dd174e79a594bf23616b3efd7570e1f047")

for repo in g.get_user().get_repos():
    print(repo.name)
    repo.edit(has_wiki=False)
    # to see all the available attributes and methods
    print(dir(repo))