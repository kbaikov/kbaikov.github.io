
# shows security issues in github actions
zizmor:
    uvx zizmor --quiet --fix .github

# updates and pins github actions to hash
pin-github-actions:
    uvx gha-update

# print date,weight,bmi,bmi_prime,cat0weight,cat1weight
# example: just weight 100.0 >> ./src/result.csv
[script('uv', 'run', '--script')]
weight weight:
    import datetime

    HEIGHT = 1.83
    date = datetime.date.today().isoformat()
    weight = {{ weight }}
    BMI = round(weight / HEIGHT**2, 1)
    BMI_Prime = round(weight / HEIGHT**2 / 25, 1)

    print(f"{date},{weight},{BMI},{BMI_Prime},3.93,5.61")
