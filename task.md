Create a Github issue to optimize existing Claude skills and agents. The goal is to reduce token usage and increase speed while keeping current quality of results. To do so:
- “plan” skill needs to be udated so that:
    - A complex model must be used (e.g. Opus 4.7) to ensure that planning is as accurate as possible.
    - if an “implementation_plan.md” file already exists at the root of the repository, it must be determined whether the plan corresponds to the task that has been requested. Then ask the user what to do, which can be:
        - Skip plan and leave implementation_plan.md in its current state, so that subsequent steps can be run at current point (this is useful if a previous execution was halted without completing the whole implementation plan).
        - Discard current implementation_plan.md and create a new one. This can happen if a previous execution could not archive implementation plan.
        - Continue with code and issue exploration and update implementation_plan, while attempting to preserve tasks that are already completed.
    - Enumerated tasks and subtasks should be grouped taking into account any related dependencies (e.g. unit or integration tests cannot be modified and run in parallel for two tasks at once, however coding and implementation of tests can be done in parallel, and then execution and validation of all tests for all tasks run once as validation). Dependencies must take into account what tasks can be run in parallel.
    - All tasks and subtasks must use a checkbox markdown placeholder (e.g. “[ ]” and be enumerated following pattern:
        - [ ] Task 1. Description,
            - [ ] Task 1.1. Description
        - etc.
    - All tasks and subtasks must indicate what language or framework they are intended for, so that proper coding skill can later be used for such language.
    - Groups of tasks must indicate whether their subtasks can be run in parallel
    - Placeholders [ ], will later be used to indicate progress of implementation.


- “code” skill must be updated so that:
    - must use a medium model (e.g. Sonnet 5), since it is assumed that all the hard reasoning must already be indicated in the implementation plan.
    - “code” skill must call “code-one-task-group” sequentially in Step 4 instead of running through each task individually, determining their language or framework and running “dotnet-code-one-task” or “java-code-one-task” skills.
    - The logic that was previously indicated in “code” skill Step 4 will be moved to skill “code-one-task-group”
    - Besides saving progress in implementation_plan.md in Step 5, the skill must notify to the user the progress of each completed group of tasks.

- “code-one-task-group” must:
    - Implement all the tasks and subtasks in a given group of tasks of the implementation plan.
    - must use a medium model (e.g. Sonnet 5) ,since it is assumed that all the hard reasoning must already be indicated in the implementation plan.
    - follow similar logic that existed in “code” skill Step 4, so that language and framework is determined for each task and subtask, and proper skill is executed (e.g. dotnet-code-one-task, java-code-one-task, or if framework/language has no explicit skill, attempt a best effort to solve the task.
    - follow similar steps to “code” Step 5, to update progress in implementation plan for each task and subtask being executed. User must also be notified when each tasks or subtask is being completed.

- create skill “dotnet-code-one-task-group”:
    - this skill is responsible to implement one group of tasks of the implementation plan for .net projects
    - must use a medium model (e.g. Sonnet 5) ,since it is assumed that all the hard reasoning must already be indicated in the implementation plan.
    - this skill will move Step 1 from “dotnet-code-one-task” to this skill, so that an initial quality baseline of the code is obtained before attempting to solve the task group by using skill “dotnet-code-quality”
    - after getting the initial quality baseline, this skill will run dotnet-code-one-task for each of the tasks of the group. If possible, tasks dispatched to “dotnet-code-one-task” skill should be run in parallel agents
    - Steps 4, 5, 6, 7, 8 and 9 of “dotnet-code-one-task” skill will also be moved to “dotnet-check-one-task-group”, so that license headers, code comments, test, coverage and quality validation is done only once per group of tasks, and if anything fails, then affected task will need to be improved. By running these steps only once per group of tasks instead of for each task, token usage is expected to be reduced while also increasing implementation speed.
    - progress of each completed task and subtask must be displayed to the user and written in the implementation_plan.md as it happens

- skill “dotnet-code-one-task” must be updated:
    - It needs to be simplified so that only steps 2, 3, 10 and 11 are preserved
    - previous quality check in step 1 and subsequent steps 4, 5, 6, 7 snd 8 will be moved to dotnet-code-one-task-group
    - this skill only needs to implement what the task specifies (Step 2) and write or update tests (Step 3)
    - the skill must use a medium model (e.g. Sonnet 5) ,since it is assumed that all the hard reasoning must already be indicated in the implementation plan.

- create skill “java-code-one-task-group”
    - this skill is responsible to implement one group of tasks of the implementation plan using java
    - must use a medium model (e.g. Sonnet 5) ,since it is assumed that all the hard reasoning must already be indicated in the implementation plan.	- this skill will move Step 1 from “java-code-one-task” to this skill, so that an initial quality baseline of the code is obtained before attempting to solve the task group by using skill “java-code-quality”
    - after getting the initial quality baseline, this skill will run java-code-one-task for each of the tasks of the group. If possible, tasks dispatched to “java-code-one-task” skill should be run in parallel agents
    - Steps 4, 5, 6, 7, 8 and 9 of “java-code-one-task” skill will also be moved to “java-check-one-task-group”, so that license headers, code comments, test, coverage and quality validation is done only once per group of tasks, and if anything fails, then affected task will need to be improved. By running these steps only once per group of tasks instead of for each task, token usage is expected to be reduced while also increasing implementation speed.
    - progress of each completed task and subtask must be displayed to the user and written in the implementation_plan.md as it happens

- skill “java-code-one-task” must be updated:
    - It needs to be simplified so that only steps 2, 3, 10 and 11 are considered
    - previous quality check in step 1 and subsequent steps 4, 5, 6, 7 snd 8 will be moved to dotnet-code-one-task-group
    - this skill only needs to implement what the task specifies (Step 2) and write or update tests (Step 3)
    - the skill must use a medium model (e.g. Sonnet 5) ,since it is assumed that all the hard reasoning must already be indicated in the implementation plan.

- skill “dotnet-code-quality” must be updated to use the simplest model (e.g. Haiku 4.5), since it only needs to process quality reports as fast as possible
- skill “dotnet-coverage” must be updated to use the simplest model (e.g. Haiku 4.5), since it only needs to process coverage reports as fast as possible
- skill “dotnet-docfx” must be updated to use a medium model (e.g. Sonnet 5), since it needs to understand code changes to generate proper documentation
- skill “dotnet-test” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to process test reports as fast as possible
- skill “antora-setup” must:
    - be renamed to “setup-antora”
    - must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs run commands in the skill
- skill “check-license” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs needs to check for license header presence and generate headers where they are missing
- skill “check-secutiry” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to process security tools reports as fast as possible
- skill “create-github-issue” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “create-jira-ticket” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “explore” must be updated to use a complex model (e.g. Opus 4.7) so that context is clearly understood when generating implementation plans by later using “plan” skill.
- skill “generate-skill-docs” must use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “issue” must use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “java-code-quality” must be updated to use the simplest model (e.g. Haiku 4.5), since it only needs to process quality reports as fast as possible
- skill “java-coverage” must be updated to use the simplest model (e.g. Haiklu 4.5) since it only needs to process coverage reports as fast as possible
- skill “ java-javadoc” must be updated to use a medium model (e.g. Sonnet 5) since it needs to understand code changes to generate proper documentation
- skill “java-test” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to process test reports as fast as possible.
- skill “pr-description” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “pr-review” must use a complex model (e.g. Opus 4.7) to ensure it has a better understanding of implementation completed by other skills.
- skill “release” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “setup-changelog” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “setup-java-github-workflows” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to use provided logic and templates
- skill “setup-java-gitignore” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to use provided examples
- skill “setup-java-library” must be updated to use the simplest model (e.g. Haiklu 4.5) since it only needs to use provided examples
- skill “setup-java-library-repository” must be updated to use the simplest model (e.g. Haiku 4.5) since it only needs to use provided examples
- skill “setup-readme” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning
- skill “update-docs” must be updated to use a medium model (e.g. Sonnet 5) to do some reasoning

The idea behind these changes is to simplify model usage on those tasks that require less reasoning, and reduce the amount of checking (coverage, code quality, license headers and security) to once per group of tasks instead of doing so for each task, so that the amount of token usage is reduced.
The impact of these changes should lead to less token usage and faster execution while achieving a similar quality.