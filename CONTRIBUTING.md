# How to contribute

We are very happy to have you contributing to our common effort!

There are many ways in which anyone can contribute:
* Add a [User Story](https://www.atlassian.com/agile/project-management/user-stories) by creating a new [issue](https://github.com/terraref/drone-pipeline/issues/new/choose)
* Document how to do something through the Drone Pipeline [wiki](ttps://osf.io/xdkcy/wiki/home/)
* Put your critiquing skills to work by reviewing a [pull requests](https://github.com/terraref/drone-pipeline/pulls); always welcome (believe it or not)
* Make a request for a new [feature](https://github.com/terraref/drone-pipeline/issues/new/choose)
* Pull up your coding chair and [resolve an issue](https://github.com/terraref/drone-pipeline/issues)
* Put in your QA/QC hat and write a test or two (TBD)

To contribute to the TERRA REF Drone Pipeline using your technical skills, please follow the workflow outlined below.

We are also happy to receive [feedback](https://github.com/terraref/drone-pipeline/issues/new/choose) on our policies and how they may, or may not, apply to you. 
We recognize that our policies are a work in progress.
If you find something that doesn't make sense, seems unnecessary, or creates an undue burden, please let us know.

When contributing to this repository, please first discuss the change you wish to make via a new [issue](https://github.com/terraref/drone-pipeline/issues/new/choose), emailing me at schnaufer@email.arizona.edu, joining our TERRA REF [slack workspace](https://terra-ref.slack.com), or any other method, with the owners of this repository before making a change. 

## Code Of Conduct
Follow the link to read our [Code of Conduct](https://github.com/terraref/drone-pipeline) stored on our GitHub repository.

## User Stories

If you want to use the drone pipeline to solve a problem you have, but aren't able to spend the time necessary for making a complete solution, consider adding a [User Story](https://github.com/terraref/drone-pipeline/issues/new/choose).

Adding a user story allows your needs to become known, and allow commenting on it to begin.
Once your user story is in the system it can be picked up and worked on by interested developers.

User stories are also a great way of providing a template on how using the drone pipeline provides a solutions.
It's possible that someone's had similar needs and reading how a solution was reached can be helpful.

## Contributing To Development

Welcome to our project!

For this project we are using:
* [git](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) for our development worflow
* [Agile](https://www.agilealliance.org/agile101/), using the [Scrum](https://www.agilealliance.org/glossary/scrum) workflow, on a two week Sprint cycle, for planning
* [OSF](https://osf.io/xdkcy/wiki/home/) as the central launching point for documentation

### Branches

We are using a 'issue branch', 'develop', and 'master' form of branching (which you may already be familiar with).
Each issue has its own branch on which development is done.
When an issue is completed, its branch is merged into the development branch **with** history compression.
To make a release, the develop branch is merged into the master branch by an authorized user.

#### Issue Branch Naming

The branch name must start with the type of development that is being done; this should be similar to the issue type.
For example, the branch for an `Issue Report` ticket would start with `issue`, and `Feature Request` would start with `feature`.

Next, the issue number directly follows the starting name, separated by a hyphen.
For example, `Task` #23 would have a starting branch name of `task-23`.

Finally a slash `/` and a very brief description is appended.
The description can contain alpha-numeric characters and hyphens.
Hyphens are used to separate words in this part of the name; underscores and other symbols are not allowed.

For example, the branch for Issue Report #7, for removing any trailing underscores from files names, could be named `issue-7/remove-trailing-chars`.
The first part, `issue-7/` is fixed and unchanging, the tailing short description could be different (`no-trailing-symbols` for example).

#### Issue Branch merging

When an issue branch is merged with the develop branch, it is deleted, resulting in the complete loss of the development history of an issue.
The goal is to reduce the amount of data to sort through to get to meaningful information.
It's important to comment on all commits to assist reviewers.
Many changes are small/short updates (or at least should be) and aren't important after reviewing and merging.
If there's something important to be considered in the future, it should be documented elsewhere.

This policy may be amended in the future.

### Documentation

You are responsible for providing new documentation for your changes.
Depending upon what the changes are, it may be necessary to create brand new documentation files.

Ask people on this project if you are unsure about where your documentation belongs.
It's possible that you're doing something new and there isn't a place for it yet.
See *How to contribute* at the top of this page to see how to contact people.

If you are considering using a documentation method not listed below, make sure that you aren't duplicating an effort.
In other words, if your documentation type already has a storage mechanism and workflow, please continue to use the established methods.
If you're onto something new that should be used, please enter an [issue](https://github.com/terraref/drone-pipeline/issues/new/choose) before proceeding.
We'd hate for your documentation to be orphaned because we can't support it.
By the same token, we'd hate to be left behind!

#### In Code
New files, classes, and methods need to be documented in code appropriately.
For Python code this means using the built-in documentation methods known as "Docstring".

If changing existing code, it's important to add at least a minimal comment above your changes containing the full issue number.
Additional information is also welcome, such as your name or initials, and what was done to effect the change.
For example, "refactored to make more efficient", or "changed loop termination check"
The issue-referencing-comments do not replace good programming style comments.

It's also important to ensure that the comments throughout the rest of the code you're touching remain accurate.

#### GitHub
The best place for a summary of changes are in the [GitHub](https://github.com/terraref/drone-pipeline) issue ticket before it's closed.
Adding a comment that summarizes the changes made as part of the issue is very helpful and can even be deemed necessary by some.

If the issue requires changes to any of the documents stored in GitHub, such as README.md, then they will need to change, obviously.

Since we are building off the [TERRA REF](https://github.com/terraref) project, any changes that impact that project need to be documented appropriately, as defined by the project.

#### Google Drive
We have been storing and sharing [technical documents](https://drive.google.com/open?id=198KRJpaHhwRNhlIkONKfc5-TqKX3ToAm) on Google Drive, but need to develop a protocol around this (TBD).

#### OSF
[OSF](https://osf.io/dashboard) is used as the central coordinating site for all Drone Pipeline documentation.
We are using the [Drone Pipeline](https://osf.io/xdkcy/wiki/home/) wiki for user level documentation and for simple collaborative documents.
Components are used to link to various projects and external storage locations.

#### Google - other
There aren't any limitations on using other Google provided tools for documentation.
There are definitely areas of documentation that are best served via a spreadsheet, presentation, or other means.
Documentation needs to be appropriately linked through the Drone Pipeline OSF site.

#### Something else
Available documentation options keep changing.
As long as it can be linked to OSF, which is also changing and growing, feel free to use other means for documenting.

### Testing

You are responsible for providing the testing criteria and environments for indicating success.
This may include providing source files, expected output, any acceptable variations on the output, and needed documentation.

### Tags

We are following [Semantic Versioning](https://semver.org/) for version numbers.
Every released version has a matching tag associated with it.

### Workflow

1. Make sure you have a [GitHub account](https://github.com/signup/free)
2. If you have a new feature or improvement, please discuss your ideas with the community on the [Slack](https://terra-ref.slack.com) channel.
3. Submit a ticket in [GitHub](https://github.com/terraref/drone-pipeline/issues) for your issue, if one doesn't exist already
  * If it's a bug, use the `Issue Report` issue template and clearly describe the issue as outlined
  * If it's a new feature or an improvement, use the `Feature Request` issue template and clearly describe all requirements and how your proposed solution would fulfill them. For complex
  new features it might help to create a [wiki page](https://osf.io/xdkcy/wiki/home/)
4. Create a fork on [GitHub](https://github.com/terraref/drone-pipeline)
5. Check out the `develop` branch
6. Make a feature/issue/task branch using the naming convention described above
7. Make your cool new feature or bug fix on your branch and update the documentation
8. From your branch, make a pull request against `develop`, being sure to point out where to find documentation updates (clearly labeled URIs are fine), and providing testing materials
9. Work with repo maintainers to get your change reviewed on GitHub via a [Pull Request](https://github.com/terraref/drone-pipeline/pulls)
10. After approval, your branch will be merged into the `develop` branch
11. Your branch will be deleted soon after being merged. Post-merge issues or changes are addressed with new tickets.

### Code Reviews

All code reviews will be part of the pull request and take place on GitHub.

### Continuous Integration

(TBD)
