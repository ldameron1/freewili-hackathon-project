Materials:

Gemini API key
Elevenlabs API
 Free WILi kit 
 two free willi wrist band things that glow and can be controlved via ir i think?
 ESp32-p4 Eye 
 
AI Tools used:

Google AI Studio
Google Antigravity
Gemini API
Elevenlabs API



Look for anything that could be clarified/simplified while still mainitnaing the needed complexity.
Fetch all relevant documentation for free willi, the gemini api, and the elevenlabs api. If there are any clarifications/additional points of interest, please specify.
There will be several modes that can be seleted from a central "launcher".
The free willi has several colored huttons, the yellow will move the selection up,
the white will move the selection down. the green button will be the "enter" button, and red 
(if we use it) will be back/cancel. (the user will be asked to rotate the device to have the free wili logo be on top of the device

Mode 1: Mafia (mvp)
	We will be implementing the ruleset of mafia as the first mode
	There will be a mode where human players will be allowed to act. 

	If a moderator is required, moderator of the game will be able to connect via a localhost connection
	on their local computer, otherwise, the game will be playable using only the free willi (all moderator functions
	occur automatically, or if some functions cannot be proframmatically automated, then using the gemini api.)
	The moderator panel will double as a debug panel, advanced features will just require the user to input the password "Debug" to enable the additional features, to ensure the user knows what they are doing.
	Switching back to standard mode will just be a button that can be clicked.
	
	For demonstration purposes, it should also be possible to have an ai-only mode. This will be useful for spot-testing the functionality, as well as a novelty generally.
	
	The game will start by randomly assinging players roles. 
	Human players will be instructed to take their free wili bands and cup their hand around the light or turn around so that others cannot
	see the color of their arm band lights. this will assign them their particular roles. (If there are only human players, then the ai features will not be needed. For debugging/testing purposes,
	There should be a debug control panel accessible via localhost to help simulate additional freewili armbands.)
	
	he ESp32-p4 Eye will be used to provide the AI agents with visual feedback on the reactions of human individuals, Humans will be asked to sit in a u-shaped formation with the free willi in the middle, to allow for everyone to see the 
	free willi and for the camera to see the free willi (as the ai agents will invoke various facial reactions. The gemini api will take the internal thoughts of the agents and their public words
	and give the agents a facial expression (emoji, or svg) to reflect their current "mood" (ie, if the agent thinks it is feeling nervous, but is trying to remail calm, then the face it shows should 
	reflect that tension. The name of the agent/personality speaking should be displlayed on the device, and each agent should have a unique voice.
	The voices of humans when they are asked to speak will be transcribed and sent to the agents (a complete conversational history/game actions log should be generated.

	
	The gemini api will be used to generate the text and actions of the various agents. The output should be in a strict json format, to ensure that the ai agent is able to play the game.
	https://ai.google.dev/gemini-api/docs/structured-output?example=recipe
	
	
	By default there will be 9 players, with there being 2 humans and 7 ai agents. The moderator control panel should allow for manual assingment of humans/agents to a specific role.
	Ai agents will have their own private thoughts/reasoning, their public statements, and will be invoke the elevenlabs api to voice their public communications.
	The voices of the agents should be piped out of the free wili's speakers.
	The moderator panel should allow for the moderator to audit the thoughts of agents (their "persona history" in essence), the overall game log. The debug mode
	should allow for the user to edit the basic personalities of the agents/specify new agents, these should be stored locally on the free wili and mirrored to the conntecting device if possible as a sort of archive
	of personalities so that in future redeployments these can be loaded back in to the agents to "play" with those agents again. (So it uses the same voice and acts generally the same way, has the same temperature settings, etc.)
	
	We should also integrate the elevenagents thing as an additional behavior mode for ai agents.
	
	Ruleset (as written by gemini):
	
	The Complete Rules of Mafia
			1. Overview and Win Conditions

			Mafia is a social deduction game for 7 to 15 players, plus one Moderator. Players are divided into two factions:

				The Town (Uninformed Majority): They do not know anyone else's roles. Their goal is to deduce who the Mafia members are and vote to eliminate them. The Town wins when all Mafia members are eliminated.

				The Mafia (Informed Minority): They know who the other Mafia members are. Their goal is to secretly eliminate the Town. The Mafia wins when the number of living Mafia members equals the number of living Town members (e.g., 2 Mafia and 2 Town), at which point they control the vote and cannot be stopped.

			2. Game Setup

				The Moderator: One person is chosen to be the Moderator. They do not play for either team. They hand out the roles, track who is alive, and run the game phases.

				Assigning Roles: The Moderator takes a deck of cards (or slips of paper) to assign roles. For a standard 9-player game, a balanced setup is: 2 Mafia, 1 Doctor, 1 Detective, and 5 Townspeople.

				The Moderator shuffles the cards and deals one face-down to each player. Players look at their card secretly, memorize their role, and keep it hidden.

			3. The Roles

				Townsperson (Town): Has no special night abilities. Their only weapon is their logic, voice, and their vote during the Day.

				Mafia (Mafia): Wakes up during the Night to collectively choose one player to eliminate.

				Doctor (Town): Wakes up during the Night and chooses one player to save. If the Mafia targets that same player, the player survives. The Doctor may choose to save themselves, but cannot choose the same person two nights in a row.

				Detective (Town): Wakes up during the Night and points to one player. The Moderator silently nods 'yes' if that player is Mafia, or shakes their head 'no' if they are Town.

			4. The Game Cycle

			The game alternates strictly between Night and Day phases, always beginning with Night 1.
			Phase 1: The Night

			The Moderator tells all players to close their eyes and put their heads down. The Moderator then reads the following script:

				"Mafia, wake up." The players with the Mafia role open their eyes. They silently communicate via pointing and eye contact to select one person they want to eliminate. Once they agree, the Moderator notes the target and says, "Mafia, go to sleep."

				"Doctor, wake up." The Doctor opens their eyes and points to one person they want to protect. The Moderator notes the choice and says, "Doctor, go to sleep."

				"Detective, wake up." The Detective opens their eyes and points to one person to investigate. The Moderator gives a thumbs up (Mafia) or thumbs down (Town). The Moderator says, "Detective, go to sleep."

			Phase 2: The Day

				The Reveal: The Moderator says, "Everyone wake up." The Moderator announces what happened during the night.

					If the Doctor did not choose the Mafia's target, the Moderator says: "Player X was killed." Player X is eliminated, must reveal their role card to the group, and can no longer speak or participate.

					If the Doctor did choose the Mafia's target, the Moderator says: "Someone was attacked last night, but the Doctor saved them." No one is eliminated.

				Discussion: The surviving players openly discuss who they believe the Mafia is. Players may lie, tell the truth, or claim to have special roles (e.g., a Mafia member might lie and say they are the Detective to get an innocent person killed).

				Nominations: At any time, a player can officially nominate another player to be eliminated. If the nomination is seconded by another player, the accused is put on trial. They are given 30 to 60 seconds to defend themselves.

				The Vote (The "Lynch"): The Moderator calls for a vote on the accused. If a strict majority (more than 50% of the living players) raises their hand to vote against the accused, that player is executed. They reveal their role and are removed from the game. The Day immediately ends.

			Phase 3: Edge Cases & Tie-Breakers

				No Majority: If the Town cannot agree and a majority is not reached, they may collectively vote to "Sleep" (or "No Lynch"). The Day ends without anyone being eliminated.

				Dead Men Tell No Tales: Eliminated players must immediately stop talking. They must keep their eyes closed during the Night phase and cannot influence the living players during the Day phase.

				Continuation: After an execution (or a vote to sleep), the game immediately transitions back to the Night phase. The cycle repeats until a win condition is met.