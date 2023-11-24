from github import Auth, Github, Issue, PullRequest


class GitHubAdapter:
    def __init__(self, github_token):
        auth = Auth.Token(github_token)
        self.g = Github(auth=auth, per_page=200)
        self.PR = {}  # set to list of known PR's (to avoid refetching)

    def get_paginated(self, fct):
        cur_page = 0
        res = []
        while True:
            next_elem = fct().get_page(cur_page)
            if next_elem:
                res += next_elem
                cur_page += 1
            else:
                return res

    def get_all_involved_pr(self):
        # Get the list of all issues
        if self.PR:
            return self.PR

        issues = self.get_paginated(self.g.get_user().get_issues)
        for i in range(len(issues)):
            self.PR[i] = issues[i]

        return self.PR

    def get_serialized_pr(self):
        issues = self.get_all_involved_pr()

        res = ""
        for key, issue in issues.items():
            res += self.serialize_issue(key, issue) + " \n"

        return res

    def serialize_issue(self, key: int, issue: Issue) -> str:
        res = ""

        res += f"Key: {key} \n"
        res += f"Title: {issue.title} \n"
        res += f"Id: {issue.id} \n"
        res += f"Body: {issue.body} \n"
        res += f"URL: {issue.html_url} \n"

        return res

    def get_pr_detail_view(self, key: int):
        """
        :param key: key of the PR in the HashMap
        :return:
        """

        return self.serialize_pr_detail_view(self.PR[key])

    def serialize_pr_detail_view(self, pr: PullRequest):
        res = ""

        return res

if __name__ == '__main__':
    GITHUB_TOKEN = "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"

    gh_adapter = GitHubAdapter(GITHUB_TOKEN)

    print(gh_adapter.get_serialized_pr())
    print(gh_adapter.get_pr_detail_view(0))
