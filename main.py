from datetime import datetime
from json import JSONEncoder
from os import environ

import requests
import json

MAX_QUERY_ATTEMPTS = 10
AFTER_PREFIX = ', after: "{cursor}"'

# We choose the first 35 repositories to avoid 502 errors from GitHub GraphQL API.
QUERY = """
    {
      search(query:"stars:>100", type:REPOSITORY, first:35 {after}) {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
          ... on Repository {
            nameWithOwner
            url
            createdAt
            updatedAt: defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 1) {
                    edges {
                      node {
                        ... on Commit {
                          committedDate
                        }
                      }
                    }
                  }
                }
              }
            }
            stargazers { totalCount }
            pullRequests { totalCount }
            acceptedPullRequests: pullRequests(states: MERGED) { totalCount }
            releases { totalCount }
            primaryLanguage{ name }
            totalIssues: issues { totalCount }
            closedIssues: issues(states: CLOSED) { totalCount }
          }
        }
      }
    }
    """


def main(token: str, results: str) -> None:
    if not token:
        if 'GITHUB_TOKEN' in environ:
            token = environ['GITHUB_TOKEN']
        else:
            raise Exception(
                "You need to set the GITHUB_TOKEN environment variable or pass your token as an argument")

    after = '' # Pagination
    repositories = [] # List of repositories
    # The process is repeated until there are amount of results wanted
    while (len(repositories) < results):
        response = get_repos(token, after)
        repositories.extend(response['search']['nodes'])
        if response['search']['pageInfo']['hasNextPage']:
            after = AFTER_PREFIX.format(cursor=response['search']['pageInfo']['endCursor'])
        else:
            break
    repositories = repositories[:results]
    export_csv(repositories)


def query_runner(query: str, token: str, attemp=1) -> dict:
    """
    This function runs a query against the GitHub GraphQL API and returns the result.
    """
    url = 'https://api.github.com/graphql'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 502 and attemp <= MAX_QUERY_ATTEMPTS:
        print('Attemp {}/{} get Error 502. Retrying...'.format(attemp, MAX_QUERY_ATTEMPTS))
        return query_runner(query, token, attemp + 1)
    elif response.status_code == 502 and attemp > MAX_QUERY_ATTEMPTS:
        print('Error 502. Maximum number of attempts reached. Try again later.')
        exit(1)
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, query))


def get_repos(token: str, after: str) -> list:
    """
    This function returns a list of the most popular repositories on GitHub and their caracteristics.
    """
    query = QUERY.replace('{after}', after)
    result = query_runner(query, token)

    if 'data' in result:
        return result['data']
    else:
        print(result)
        raise Exception('Error getting repositories. Message: {}. \n {}'.format(result['message'], query))


def export_csv(repos: list) -> None:
    """
    This function exports the list of repositories to a CSV file.
    """
    with open('output.csv', 'w') as f:
        f.write('nameWithOwner,url,createdAt,updatedAt,stargazers,pullRequests,acceptedPullRequests,releases,primaryLanguage,totalIssues,closedIssues\n')
        for repo in repos:
            repo['primaryLanguage'] = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else ''
            repo['createdAt'] = datetime.strptime(repo['createdAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
            repo['updatedAt'] = repo['updatedAt']['target']['history']['edges'][0]['node']['committedDate']
            repo['updatedAt'] = datetime.strptime(repo['updatedAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')

            f.write('{},{},{},{},{},{},{},{},{},{},{}\n'.format(
                repo['nameWithOwner'],
                repo['url'],
                repo['createdAt'],
                repo['updatedAt'],
                repo['stargazers']['totalCount'],
                repo['pullRequests']['totalCount'],
                repo['acceptedPullRequests']['totalCount'],
                repo['releases']['totalCount'],
                repo['primaryLanguage'],
                repo['totalIssues']['totalCount'],
                repo['closedIssues']['totalCount']
            ))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Query the GitHub GraphQL API to get most popular repositories.')
    parser.add_argument('--token', '-t', help='GitHub access token')
    parser.add_argument('--results', '-r', help='Number of results to return', type=int, default=100)
    args = parser.parse_args()

    main(args.token, args.results)
