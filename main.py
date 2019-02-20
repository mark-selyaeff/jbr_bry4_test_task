import json  # json parsing tool
import jsonlines  # for writing entities to a file
import itertools
import requests  # lib for querying websites


def get_list_url(n_changes: int, offset: int):
    return f"https://git.eclipse.org/r/changes/?n={n_changes}&O=81&S={offset}"


def get_details_url(change_id: int):
    return f"https://git.eclipse.org/r/changes/{change_id}/detail?O=10004"


def is_bot(reviewer_name: str):
    return True if 'bot' in reviewer_name.lower() else False


def get_changes(chunk_size=50):
    """This generator gets a list of changes from internal API and parses it to JSON """
    for offset in itertools.count(start=0, step=chunk_size):
        r = requests.get(get_list_url(chunk_size, offset))
        try:
            changes = json.loads(r.content[5:])
        except json.JSONDecodeError:
            raise StopIteration
        if not changes:
            return  # stop generator
        yield from changes


def get_reviews():
    """This generator calls detail API for every change with code review available.

    It gathers all information (reviewers usernames, their comments and a bot flag)
    into dictionary.
    """
    for change in get_changes(100):
        if not change['labels']['Code-Review']:
            continue
        author = change['owner'].get('username', "NA")
        change_details = {'change_id': change['_number'], 'author': author,
                          'reviewers': dict()}
        r = requests.get(get_details_url(change['_number']))
        try:
            details = json.loads(r.content[5:])
        except json.JSONDecodeError:
            continue
        for msg in details['messages']:
            try:
                reviewer = msg['author']['name']
                if reviewer in change_details['reviewers']:
                    change_details['reviewers'][reviewer]['messages'].append(
                        msg['message'])
                else:
                    change_details['reviewers'][reviewer] = {}
                    change_details['reviewers'][reviewer]['messages'] = [msg['message']]
                    change_details['reviewers'][reviewer]['is_bot'] = is_bot(reviewer)
            except KeyError as e:
                print(e)
                print(details)
        yield change_details


if __name__ == "__main__":
    N_REVIEWS = 10000  # number of reviews to download
    reviews = get_reviews()  # init generator

    with jsonlines.open('reviewers.jsonl', 'w') as f:
        for idx, review in enumerate(reviews):
            if idx > N_REVIEWS:
                break
            f.write(review)
            print(f"{idx}th entity written to a file...")
