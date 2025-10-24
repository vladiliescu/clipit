# A simple release checklist

- [ ] Update the version number in `pyproject.toml`
- [ ] Sync the content in README.md with the latest changes in `grabit.py` and git log. Manually review them as they'll most likely contain some gibberish as well.

###
@grabit.py @readme.md

Help me update the readme file with the latest updates in `grabit.py`. Remember to split the release notes into new features and fixes. If it helps, here's the git log:

```
output of `git log v<previous_version>..HEAD --pretty=format:"%h %ad | %s%d [%an]" --date=short`
```

(and use this for the new release)

###

- [ ] Merge dev into main

```sh
git checkout main
git merge dev --ff-only
```

- [ ] Tag new release in git

```sh
git tag vX.Y.Z
git push origin main --tags
```



- [ ] Create a new release on GitHub with the release notes
- [ ] Make sure to include the latest grabit.py in the release