# How to contribute

We are very happy to have you contributing to our common effort!
To contribute to the TERRA REF Drone Pipeline, please follow the workflow outlined below.

We are also happy to receive [feedback][https://github.com/terraref/drone-pipeline/issues/new/choose] on our policies and how they may, or may not, apply to you. 
Note that policies need to be followed regardless of how you may feel about them.

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change. 

## User Stories

If you want to use the drone pipeline to solve a problem you have, but aren't able to spend the time necessary for making a complete solution, consider adding a [User Story][https://github.com/terraref/drone-pipeline/issues/new/choose].

Adding a user story allows your needs to become known and commenting on it to begin.
Once your user story is in the system it can be picked up and worked on by interested developers.

User stories are also a great way of providing a template for using the drone pipeline to provide solutions.
It's possible that someone has had similar needs and by reading how they reached a solution can be helpful.

## Branches

We are using a 'issue branch', 'develop', and 'master' form of branching (which you may already be familiar with).
Each issue has it's own branch on which development is done.
When an issue is completed, its branch is merged into the development branch **with** history compression.
To make a release, the develop branch is merged into the master branch by an authorized user.

### Issue Branch Naming

The branch name must start with the type of development that is being done; this should be simmilar to the issue type.
For example, the branch for an `Issue Report` ticket would start with `issue`, and `Feature Request` would start with `feature`.

Next, the issue number directly follows the starting name, separated by a hyphen.
For example, `Task` #23 would have a starting branch name of `task-23`.

Finally a slash `/` and a very brief description is appended.
The description can contain alpha-numeric characters and hypens.
Hyphens are used to separate words in this part of the name; underscores and other symbols are not allowed.

For example, the branch for Issue Report #7, for removing any trailing underscores from files names, could be named `issue-7/remove-trailing-chars`.
The first part, `issue-7/` is fixed and unchanging, the tailing short description could be different (`no-trailing-symbols` for example).

### Issue Branch merging

When an issue branch is merged with the develop branch, it is deleted, resulting in the complete loss of the development history of an issue.
The goal is to reduce the amount of data to sort through to get to meaningful information.
It's important to comment on all commits to assist reviewers.
Many changes are small/short updates (or at least should be) and aren't important after reviewing and merging.
If there's something important to be considered in the future, it should be documentated elsewhere.

This policy may be ammended in the future.

## Documentation

You are responsible for providing new documentation for your changes.
Depending upon what the changes are, it may be necessary to create brand new documentation files.

## Testing

You are responsible for providing testing criteria and environments for indicating success.
This may include providing source files, expected output, any acceptable variations on the output, and needed documentation.

## Tags

We are following [Semantic Versioning][https://semver.org/] for version numbers.
Every released version has a matching tag associated with it.

## Workflow

1. Make sure you have a [GitHub account](https://github.com/signup/free)
2. If you have a new feature or improvement, please discuss your ideas with the community on the [Slack][https://terra-ref.slack.com] channel.
3. Submit a ticket in [GitHub][https://github.com/terraref/drone-pipeline/issues] for your issue, if one doesn't exist already
  * If it's a bug, use the `Issue Report` issue template and clearly describe the issue as outlined
  * If it's a new feature or an improvement, use the `Feature Request` issue template and clearly describe all requirements and how your proposed solution would fulfill them. For complex
  new features it might help to create a [wiki page][https://github.com/terraref/drone-pipeline/wiki]
4. Create a fork on [GitHub][https://github.com/terraref/drone-pipeline]
5. Check out the `develop` branch
6. Make a feature/issue/task branch using the naming convention described above
7. Make your cool new feature or bugfix on your branch and update the documentation
8. From your branch, make a pull request against `develop`, being sure to point out where to find documentation updates (clearly labeled URIs are fine), and providing testing materials
9. Work with repo maintainers to get your change reviewed on [GitHub][https://github.com/terraref/drone-pipeline]
10. After approval, your branch will be merged into the `develop` branch
11. Your branch will be deleted soon after being merged. Post-¬merge issues or changes are addressed with new tickets.

## Code Reviews

All code reviews will be part of the pull request and take place on GitHub.

## Continuous Integration

(TBD)

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or
advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic
  address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

### Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in
response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or
reject comments, commits, code, wiki edits, issues, and other contributions
that are not aligned to this Code of Conduct, or to ban temporarily or
permanently any contributor for other behaviors that they deem inappropriate,
threatening, offensive, or harmful.

### Scope

This Code of Conduct applies both within project spaces and in public spaces
when an individual is representing the project or its community. Examples of
representing a project or community include using an official project e-mail
address, posting via an official social media account, or acting as an appointed
representative at an online or offline event. Representation of a project may be
further defined and clarified by project maintainers.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported by contacting the project team at [INSERT EMAIL ADDRESS]. All
complaints will be reviewed and investigated and will result in a response that
is deemed necessary and appropriate to the circumstances. The project team is
obligated to maintain confidentiality with regard to the reporter of an incident.
Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good
faith may face temporary or permanent repercussions as determined by other
members of the project's leadership.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at [http://contributor-covenant.org/version/1/4][version]

[homepage]: http://contributor-covenant.org
[version]: http://contributor-covenant.org/version/1/4/