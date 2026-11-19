# Learned guidelines: GPT-6 Luna, Revised, run 3

102 generic and 1 example-specific error-driven guidelines; 47 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-005** (T5; refines FLOW-01; 20 description(s); confirmed: yes)  
When the description presents distinct activities in an ordered progression, including transitions into, through, or out of branches or synchronization points: Connect each consecutive activity with a sequence flow, preserving the stated transitions through branches and synchronization points.

**LRN-012** (T6; refines FID-03; 19 description(s); confirmed: yes)  
When the description states a specific activity or process-ending outcome: Label the corresponding BPMN activity or end event with a concise phrase that preserves the stated action or outcome; do not substitute a related action or add an unsupported one.

**LRN-006** (T5; refines GW-04; 14 description(s); confirmed: yes)  
When the description names multiple required activities without specifying their order and states that a later outcome depends on all of them: Model the activities as parallel branches and synchronize them before that outcome.

**LRN-070** (T6; refines FID-03; 14 description(s); confirmed: yes)  
When the description states an activity, its object, scope, or recipient: Label the corresponding BPMN element so that it preserves the described action, object, scope, and direction; do not replace them with a related action or add unsupported details.

**LRN-052** (T6; refines FID-03; 10 description(s); confirmed: no)  
When the description identifies a specific trigger, decision criterion, or performed activity: Use a concise BPMN label that expresses that meaning; do not substitute a related event, outcome, or different decision.

**LRN-016** (T5; refines FID-01; 8 description(s); confirmed: yes)  
When the description identifies work performed by a participant as the first step of the process: Model that work as an activity after a start event and before the subsequent activity; do not represent the work itself as the start event.

**LRN-009** (T5; refines GW-03; 7 description(s); confirmed: yes)  
When the description presents mutually exclusive alternatives or says an activity may or may not occur, and the paths later continue in common: Model the choice with an exclusive gateway, and reconnect the alternative paths with an exclusive merge before their shared continuation.

**LRN-059** (T5; refines FID-01; 6 description(s); confirmed: yes)  
When the description states that an action should be taken depending on the outcome of a condition: Model the condition with an exclusive gateway and represent each stated follow-up action as a task on its applicable branch.

**LRN-021** (T6; refines FID-03; 5 description(s); confirmed: no)  
When the description states an activity with explicit alternatives or qualifiers that distinguish its scope: Label the corresponding BPMN element concisely while preserving those stated distinctions; do not generalize them away.

**LRN-055** (T5; refines PROC-03; 5 description(s); confirmed: no)  
When the description indicates that a decision or synchronization follows an activity: Connect the activity to the appropriate gateway, and connect each gateway branch to its stated continuation or outcome.

**LRN-017** (T6; refines FID-03; 4 description(s); confirmed: no)  
When the description states an activity together with criteria, optional supporting actions, or a later outcome associated with it: Label the BPMN task with a concise verb-object phrase for the activity itself. Keep associated criteria, alternatives, and subsequent outcomes out of the label unless they define the activity.

**LRN-025** (T5; refines FID-01; 4 description(s); confirmed: yes)  
When the description identifies a concrete action that initiates the process: Model that action as an activity after the start event, and connect it by sequence flow to the next described activity.

**LRN-028** (T6; refines FID-03; 4 description(s); confirmed: yes)  
When the description states what initiates the process or identifies the outcome at which it ends: Label the corresponding start or end event with a concise phrase that faithfully names that stated boundary, rather than a generic label or a related intermediate activity.

**LRN-003** (T6; refines FID-01; 3 description(s); confirmed: no)  
When the description explicitly states the outcome or condition at which the process ends: Label the end event with that stated outcome rather than a generic or unspecified ending.

**LRN-018** (T6; new; 3 description(s); confirmed: no)  
When the description states that one participant sends information to another participant: Model and label the activity from the sender’s perspective as sending the information, rather than as the recipient receiving it.

**LRN-031** (T3; refines GW-06; 3 description(s); confirmed: yes)  
When the description names multiple activities that must all occur and another activity that occurs only in certain cases as part of the same stage: Model the required activities and the conditional activity so synchronization waits for all required work but only for conditional branches that were activated; use an inclusive split and join rather than a parallel join that waits for every possible branch.

**LRN-035** (T6; refines FID-03; 3 description(s); confirmed: no)  
When the description identifies a role or group as responsible for performing an activity: Label the corresponding BPMN activity so that the stated responsibility remains clear, without adding unstated details.

**LRN-038** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description states distinct conditions for different decisions or qualifies an activity separately from a decision: Label each BPMN gateway with the condition it actually represents; do not transfer a condition from a separate decision or activity.

**LRN-001** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description states a conditional outcome followed by intervening actions or an approval before a later activity: Model the branch through the described intervening actions and approval in the stated order; do not connect it directly to a later activity that bypasses them.

**LRN-002** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description states a conditional path but does not specify what happens when the condition is false: If an end event is modeled for that unspecified path, label it neutrally rather than assigning an unstated outcome.

**LRN-004** (T1; refines XML-03; 2 description(s); confirmed: yes)  
When the description is being translated into a BPMN XML model: Assign every BPMN element an id that is a valid XML Schema xs:ID value, following the XML name lexical rules, and ensure the ids are unique.

**LRN-008** (T5; refines GW-02; 2 description(s); confirmed: yes)  
When the description says an activity may or may not take place: Model the choice with an exclusive split: one path performs the optional activity and the other bypasses it. Rejoin the alternative paths with an exclusive merge when both continue into the same flow.

**LRN-013** (T5; refines GW-01; 2 description(s); confirmed: no)  
When the description states that a condition determines whether an action or process path is needed: model the choice with an exclusive gateway and conditional branches for the possible outcomes.

**LRN-014** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description explicitly identifies a role or participant as responsible for performing an activity: Represent that responsibility in the corresponding activity label or in the responsible lane; do not leave the responsibility unrepresented when the description states it.

**LRN-020** (T6; refines FID-02; 2 description(s); confirmed: yes)  
When the description names multiple distinct evaluation objectives for a single item: Model each stated objective as a separate BPMN task rather than grouping the objectives into one task.

**LRN-023** (T5; refines FID-02; 2 description(s); confirmed: yes)  
When the description presents ongoing work alongside another activity but does not state that both must finish before a later milestone or transition: Do not add a parallel join that makes completion of both activities a prerequisite for that milestone or transition.

**LRN-029** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that a concrete action is performed to produce or deliver an outcome before the process reaches its stated terminal outcome: model the concrete work as a task and then use an end event for the terminal outcome

**LRN-032** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that a condition triggers a distinct activity: Model the activity as a task on the branch where the condition holds; do not omit it or represent it only as a branch outcome.

**LRN-034** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description attributes an action that prompts further work to a specific actor: Label the corresponding activity with that actor performing the stated action, rather than recasting it from the perspective of another participant receiving or handling it.

**LRN-039** (T7; refines FID-01; 2 description(s); confirmed: yes)  
When the description says an internal role solicits offers from outside organizations and chooses among them: Model the stated solicitation and selection work in the internal process. Do not add separate participant pools or message flows for the outside organizations unless the description establishes them as process participants exchanging messages.

**LRN-041** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description states a decision criterion or outcome that determines a branch: Label the corresponding gateway with a concise phrase that expresses that criterion or outcome, rather than a generic question.

**LRN-042** (T7; refines COL-01; 2 description(s); confirmed: yes)  
When the description focuses on one participant’s workflow and mentions an outside party only as the recipient or source of requests, payments, or responses, without describing that party’s own process: Model the described workflow within its participant pool; do not add a separate pool or message flows solely to represent those mentions. Represent relevant receipt or decision points within the described process.

**LRN-050** (T3; refines PROC-04; 2 description(s); confirmed: no)  
When the description states that the process ends under one condition but, under another, continues with additional or recurring work: Model the continuing alternative as a branch connected to the existing process flow, rather than as a detached start-to-end chain.

**LRN-060** (T5; refines FLOW-07; 2 description(s); confirmed: no)  
When the description says an activity is repeated until a stated condition is met: Model a decision after the repeated activity, routing the unmet condition back to repeat the activity and the met condition onward.

**LRN-063** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states an initiating goal or intent, followed by preparatory work that must happen before the primary operation begins: Represent the initiating goal or intent with a start event, and model each stated preparatory action as an activity before the primary operation.

**LRN-064** (T5; new; 2 description(s); confirmed: no)  
When the description says information is sent to an external participant and a later decision or continuation depends on that participant's response: Model the response as an intermediate message catch event before the dependent decision or work; do not model receiving the response as a task or as a process start unless the description states a separate incoming trigger.

**LRN-073** (T5; refines ACT-05; 2 description(s); confirmed: no)  
When the description says that an external response or completion is awaited while other work can proceed in parallel: Model the awaited response or completion as an intermediate catch event on a parallel branch, and synchronize that branch with the other work before continuing.

**LRN-076** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description says that an automated system makes information available to another participant: Label the service activity from the system’s perspective, using its action of providing or presenting the information rather than the recipient’s act of receiving it.

**LRN-092** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description presents multiple activities that can follow the same preceding activity and does not specify an order between them: Model the activities as parallel branches using a parallel gateway.

**LRN-098** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant may perform one of several alternative actions: Model each stated action as an activity on its corresponding decision branch; do not represent the actions only as alternative end events.

**LRN-007** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description explicitly identifies an action or process milestone at a point in the flow: Label the corresponding BPMN task with that stated action or milestone; do not substitute a related action or label only a constituent activity when the description identifies the broader milestone.

**LRN-010** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states a distinct handling action to be performed after an item or material is received: Model that handling action as a BPMN activity in the described flow; do not omit it or absorb it into another activity.

**LRN-011** (T5; refines GW-03; 1 description(s); confirmed: yes)  
When the description identifies mutually exclusive destinations for an item or output: Model each destination as a distinct activity on an exclusive branch, then merge the branches before their shared continuation.

**LRN-015** (T5; refines GW-01; 1 description(s); confirmed: yes)  
When the description places ongoing activities within a stated period and separately says that the period ends before subsequent work, without explicitly requiring those activities to finish first: Model the period-ending trigger as a timer catch event leading to the subsequent work; do not add a parallel join that waits for every ongoing activity to complete unless the description requires that synchronization.

**LRN-019** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant supplies information needed for a later processing step: Model the information-supplying action as an activity before the processing that depends on that information.

**LRN-022** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description states a milestone followed by later activities or ongoing support before the process is complete: Label the end event with the actual process-ending outcome, not with an earlier milestone; keep that milestone on its corresponding activity.

**LRN-024** (T6; refines PROC-05; 1 description(s); confirmed: no)  
When the description says that participants may perform a follow-up activity after the main outcome has been reached: Model the follow-up activity as optional and post-completion; represent its relationship to the main flow without making it a required step before the main outcome.

**LRN-026** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states that an activity evaluates information and communicates a resulting outcome to another participant: Label the corresponding task to preserve both the evaluation and the communication, rather than naming only the communication.

**LRN-027** (T5; refines SUB-05; 1 description(s); confirmed: yes)  
When the description states that evaluation findings may prompt repeated changes, and that resulting changes require authorization: Model the communication of findings, the change, and its authorization as distinct activities in a repeatable cycle that returns to evaluation when another round is needed.

**LRN-030** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a review is performed and separately identifies findings from that review: Model the review and the identification of findings as distinct BPMN tasks when they are described as separate activities.

**LRN-033** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a check or inspection is carried out on the result of an activity: model the check or inspection as a distinct task after that activity and before the next described work

**LRN-036** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states an action from the perspective of the person or participant receiving a service, item, or information: Label the BPMN activity to preserve the direction and perspective stated in the description; do not recast it as the corresponding sender-side action.

**LRN-037** (T5; refines GW-03; 1 description(s); confirmed: yes)  
When the description says an optional follow-up can occur after an outcome and that each occurrence requires the outcome to happen again: Model the follow-up as a repeat path to that outcome, joining the initial path at an exclusive merge before the outcome.

**LRN-040** (T7; refines LANE-01; 1 description(s); confirmed: yes)  
When the description assigns activities in one organizational process to multiple internal roles: Represent the organization’s process in one participant pool and use lanes for the stated internal roles; do not omit the process pool or model ordinary internal roles as separate pools.

**LRN-043** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a condition leads to a distinct activity or to ending the case: Model each stated outcome on its corresponding branch, connecting it to the required activity or end; do not omit the activity or leave the outcome without a modeled destination.

**LRN-044** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description uses first-person narration to identify the actor performing the workflow: model that actor’s described workflow within a participant pool, rather than leaving the workflow without an explicit participant

**LRN-045** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description says a person uses a software interface to start a process in another system and receives the process outcome through that interface: Model the interface as a separate participant pool and represent the request and returned information with message flows between it and the system process.

**LRN-046** (T5; refines ACT-05; 1 description(s); confirmed: yes)  
When the description distinguishes an incoming notice about a delay or status change from a subsequent communication of that information to a user: Model receipt of the incoming notice as a catching message event, and model the user-facing communication as a separate task.

**LRN-047** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description distinguishes communication activities by the information conveyed or by their direction: label each communication activity to reflect its own message content and whether the participant sends or receives it, rather than using a label for a different exchange

**LRN-048** (T7; refines COL-07; 1 description(s); confirmed: yes)  
When the description states that distinct roles in an organization send information to one another about their work: model those roles as separate participant pools and represent each stated exchange with a message flow

**LRN-049** (T7; refines COL-04; 1 description(s); confirmed: yes)  
When the description states that one participant sends information, a request, or an item to another participant: Model the stated exchange as a message flow from the sending participant to the receiving participant, connecting appropriate interaction nodes in their respective pools and directing the flow from sender to receiver.

**LRN-051** (T5; refines ACT-08; 1 description(s); confirmed: no)  
When the description states that a person must supply or enter information: Model that human-performed activity as a user task rather than as a generic task.

**LRN-053** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that two parties can each perform a reciprocal action toward the other: Model each party’s stated action separately; do not omit one direction.

**LRN-054** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description specifies multiple required reports or notifications with separate eligibility criteria, and one case may meet more than one criterion: Model each criterion as an independently evaluated decision path and connect every qualifying path to its corresponding reporting action, allowing multiple paths to proceed for the same case.

**LRN-056** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description mentions multiple activities without stating that one precedes, triggers, or depends on another: Do not connect those activities with a sequence flow; model only the order or dependency that the description establishes.

**LRN-057** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description lists documents or other materials required for an application and says that additional materials may be requested: Model an activity to prepare or provide the required materials before the application proceeds. If further materials may be requested, model a conditional follow-up to provide them.

**LRN-058** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says a decision about whether to proceed depends on replies from multiple participants, and an earlier choice is repeated when the decision condition is not met: Model an intermediate catch event for the replies before evaluating the condition, and loop an unmet result back to the activity that makes the choice.

**LRN-061** (T3; refines PROC-05; 1 description(s); confirmed: yes)  
When the description says an event can occur while work is ongoing and affect that work: Model the event handling within the affected process scope, using an appropriate boundary event or event subprocess. Keep sequence flows within the same process or subprocess scope; use message flows for interactions between separate participants.

**LRN-062** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description assigns a person to configure or initiate work that is then performed by an automated system: Model the person and system as lanes within the same participant pool, and place the process start event in the lane responsible for initiating the work.

**LRN-065** (T1; refines SUB-05; 1 description(s); confirmed: no)  
When the description states that an activity is performed for each of multiple items or instances, with a specified iteration count or sequential/parallel execution setting: Model the repetition with BPMN multi-instance loop characteristics, placing iteration count and sequential/parallel settings on that construct. Use standard-loop characteristics for loop conditions, and ensure each property is valid for its BPMN loop type.

**LRN-066** (T3; refines EVT-01; 1 description(s); confirmed: no)  
When the description indicates that a process or subprocess starts before work is performed: Connect its start event by an outgoing sequence flow to the first activity or gateway in the same scope.

**LRN-067** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a resource or supply must be replenished when it is depleted, while work can otherwise continue: Model the depletion condition as a decision with an explicit branch to the replenishment activity and a branch that continues without replenishment.

**LRN-068** (T1; refines SUB-05; 1 description(s); confirmed: yes)  
When the description states that an activity is repeated for multiple items or instances: Model the repetition with the appropriate BPMN loop-characteristics type, and use only the attributes and child elements permitted for that type.

**LRN-069** (T6; refines EVT-03; 1 description(s); confirmed: no)  
When the description states that subsequent work begins only after an item or material arrives: Model the wait for arrival as an intermediate catch event before the dependent work, rather than as a task representing the arrival itself.

**LRN-071** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says a dependent activity can begin when the first of several expected arrivals occurs, while other arrivals may still be pending: Model the arrival in the ongoing process flow as an intermediate catch event, and let it enable the dependent activity without waiting for all expected arrivals or using it to start a new process.

**LRN-072** (T5; refines GW-06; 1 description(s); confirmed: no)  
When the description gives multiple threshold conditions on the same measure whose ranges overlap: model each applicable action as a branch that can be activated independently, using an inclusive split rather than mutually exclusive routing

**LRN-074** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description says that an outside participant performs work of its own or returns information after receiving input, rather than merely naming that participant as a recipient or source: Model that participant as a separate pool and represent the described exchanges with message flows between valid interaction nodes; keep the initiating participant’s work in its own pool.

**LRN-075** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that prepared items are subsequently ordered or submitted in a transaction: Model placing or submitting the order as a distinct activity sequenced after the preparation activity.

**LRN-077** (T5; new; 1 description(s); confirmed: yes)  
When the description makes an action depend on whether a measured result satisfies a stated criterion: Model the criterion with a decision gateway and connect each supported outcome to its corresponding path.

**LRN-078** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that work resumes after a triggering event within an ongoing process: Model the resumed work as an activity in the existing process flow, rather than as a new process start event.

**LRN-079** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description says to collect information from a source and calculate a metric that depends on that information: Model the information-gathering work needed to obtain the inputs as activity or activities before the calculation; do not omit that work when modeling the calculation.

**LRN-080** (T5; refines GW-06; 1 description(s); confirmed: no)  
When the description identifies multiple kinds of work during the same stage and states that additional work occurs only when a condition holds: Model the work required in every case as parallel branches. Model condition-dependent work with an inclusive split and join so that only activated branches are synchronized.

**LRN-081** (T5; refines GW-01; 1 description(s); confirmed: no)  
When the description states that whether additional activities occur depends on the outcome of earlier work: Model the alternatives with an exclusive gateway, and label its outgoing sequence flows with the conditions that determine whether the additional activities occur.

**LRN-082** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description states that an external participant is expected to arrive after an activity, without specifying an exact time: Model the wait for that arrival as an intermediate catch event following the activity.

**LRN-083** (T5; new; 1 description(s); confirmed: no)  
When the description states that an activity may not occur and that a consequence follows if it has not occurred by a stated deadline: Model the possible activity and its non-occurrence as alternative paths; represent the deadline with a timer event before modeling the consequence.

**LRN-084** (T5; refines ACT-03; 1 description(s); confirmed: no)  
When the description says an automated system checks whether a condition holds and subsequent work depends on the result: Model the check as a service task, then use an appropriate gateway to route the flow according to its result.

**LRN-085** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description specifies a follow-up for one outcome of a decision but does not state what happens for the alternative outcome: Model the stated outcome and its follow-up, but do not invent a separate activity or end event for the unspecified alternative.

**LRN-086** (T5; new; 1 description(s); confirmed: no)  
When the description states that one participant offers another a choice among alternatives and the other participant's selection determines the subsequent process path: Model the participant's selection as a user task before the gateway that routes the process according to the selected alternative.

**LRN-087** (T5; new; 1 description(s); confirmed: no)  
When the description says an action recurs at fixed time intervals while another activity is in progress: Model the recurring action on a path that can repeat, using a timer catch event to represent each time-based trigger, and connect that path to the activity performed in response.

**LRN-088** (T3; refines PROC-03; 1 description(s); confirmed: yes)  
When the description presents one process trigger followed by subsequent work and does not state a distinct trigger for another process start: Connect the subsequent work to the flow from the stated trigger; do not model it as a detached start-to-end chain.

**LRN-089** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description makes a follow-up action depend on whether a waiting period exceeds a stated duration: model the duration check with an exclusive gateway after the wait, route the conditional action along its applicable branch, and merge the paths before their shared continuation

**LRN-090** (T5; refines FLOW-06; 1 description(s); confirmed: no)  
When the description says that items are processed iteratively, that overall completion is checked after an item is processed, and that an incomplete result leads to selecting another item and repeating the item-level check: Model the item-processing outcomes to converge before the overall completion check, and route the incomplete outcome through the next-item selection back to the item-level check.

**LRN-091** (T6; refines EVT-06; 1 description(s); confirmed: no)  
When the description gives a process title but states no explicit start trigger: Label the start event with a concise form of the process title rather than a generic label.

**LRN-093** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description defines a decision by comparing two time points over a stated duration: Label the decision condition so both time points and the duration being compared are clear.

**LRN-094** (T3; new; 1 description(s); confirmed: yes)  
When the description says that a result determines whether the process finishes or performs another activity selected from alternatives: Model the result as an exclusive choice, route execution only through the selected alternative or to completion, and do not use a parallel join that waits for tokens from mutually exclusive paths. Represent any required repetition explicitly.

**LRN-095** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an item is reviewed and separately describes an approval, rejection, or marking action before outcomes are chosen: Model each separately stated review and approval, rejection, or marking action as its own BPMN activity, followed by an exclusive gateway for the stated outcome paths; do not use the gateway itself to stand in for an action.

**LRN-096** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that an item is received by a specific role after a preceding activity: Model the receipt as a distinct activity assigned to the receiving role, preserving its stated sequence; do not use a generic receipt activity that omits the recipient.

**LRN-097** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes an initial submission or initiation from a subsequent registration of the item before another activity: Model the submission and the subsequent registration as separate activities, preserving their stated order and dependency.

**LRN-099** (T5; refines ACT-04; 1 description(s); confirmed: no)  
When the description states that one participant sends information or an item to another participant: Model the sending action as a Send Task rather than a generic Task.

**LRN-100** (T5; new; 1 description(s); confirmed: yes)  
When the description states that a participant responds after assessing an input, and that the response depends on the assessment result: Model the response as an activity following the assessment, and use an exclusive gateway to route each stated response outcome to its corresponding path.

**LRN-101** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that one participant sends information to another and the recipient’s next stated step is to process it: Model the stated sending activity and the recipient’s processing step, using flows appropriate to the participant structure. Do not insert an unsupported waiting gateway or separate receiving activity unless the description indicates one.

**LRN-102** (T5; refines GW-03; 1 description(s); confirmed: yes)  
When the description says an activity is reached from the initial route and from one or more routes that return after a condition is not met: model an exclusive merge gateway before the activity to converge the alternative incoming paths

## Example-specific guidelines

**EXS-007** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says one participant communicates a delay to another participant before continuing its own work: Model the notification as a message send task in the sender’s process, and model receipt separately as a message catch event in the recipient’s process when receipt is stated.
