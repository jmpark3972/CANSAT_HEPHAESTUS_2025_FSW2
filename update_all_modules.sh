git pull
git submodule foreach "git checkout main || :"
git submodule foreach "git pull || :"
