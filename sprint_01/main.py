import requests
import json
from os import environ

def query_runner(query: str, token: str) -> dict:
    """
    This function runs a query against the GitHub GraphQL API and returns the result.
    """
    url = 'https://api.github.com/graphql'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, query))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Query the GitHub GraphQL API to get most popular repositories.')
    parser.add_argument('--token', '-t', help='GitHub access token')
    args = parser.parse_args()

    if not args.token:
        if 'GITHUB_TOKEN' in environ:
            args.token = environ['GITHUB_TOKEN']
        else:
            raise Exception(
                "You need to set the GITHUB_TOKEN environment variable or pass your token as an argument")
