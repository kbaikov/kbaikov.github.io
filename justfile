
# shows security issues in github actions
zizmor:
    uvx zizmor --gh-token $(gh auth token) --quiet --fix .github

# updates and pins github actions to hash
pin-github-actions:
    uvx gha-update

# append to src/result.csv date,weight,bmi,bmi_prime,cat0weight,cat1weight
# example: just weight 100.0
[script('uv', 'run', '--script')]
weight weight:
    import datetime

    cat0weight = 3.93
    cat1weight = 5.61
    FILE = "src/result.csv"
    HEIGHT = 1.83
    date = datetime.date.today().isoformat()
    weight = {{ weight }}
    BMI = round(weight / HEIGHT**2, 1)
    BMI_Prime = round(weight / HEIGHT**2 / 25, 1)

    with open(FILE, "a") as file:
        file.write(f"{date},{weight},{BMI},{BMI_Prime},{cat0weight},{cat1weight}\n")
