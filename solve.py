import urllib.request
import random
import os
import json
import math
import operator
import subprocess
import time
import sys
import logger
from PIL import Image

#
# Copyright <2017> <ANDREAS KRUHLMANN>
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation 
# files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, 
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons 
# to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE 
# AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# Path where maze replays will be stored
base_path = os.path.join(os.environ["HOMEPATH"], "Desktop\\Mazes")

# This is defined in the challenge. Fits nicely into a 16:9 default CMD.
maze_width = 15
maze_height = 25

spinner = [".  ", ".. ", "..."]

valid_directions = [
	"north",
	"south",
	"east",
	"west"
]

# Pulled this from the wiki, seems they are all valid; could be more.
pony_names = [
	"Fluttershy",
	"Twilight Sparkle",
	"Applejack",
	"Rainbow Dash",
	"Pinkie Pie",
	"Rarity",
	"Spike"
]

api_calls = {
	"create_maze": "https://ponychallenge.trustpilot.com/pony-challenge/maze",
	"get_maze": "https://ponychallenge.trustpilot.com/pony-challenge/maze/{0}",
	"print_maze": "https://ponychallenge.trustpilot.com/pony-challenge/maze/{0}/print"
}

# Generates a maze by sending an HTTP request to the API. Maze ID is included in the JSON response
def create_maze():
	payload = {
		"maze-width": maze_width,
		"maze-height": maze_height,
		"maze-player-name": random.choice(pony_names)
	}
	payload_json = json.dumps(payload).encode("utf-8")
	try:
		req = urllib.request.Request(api_calls["create_maze"], data=payload_json, headers={'Content-Type': 'application/json'})
		response = urllib.request.urlopen(req)
		json_response = json.loads(response.read().decode("utf-8"))
		return {
			"response": json_response["maze_id"],
			"payload": payload,
			"error": ""
		}
	except ValueError as e:
		return {"error": "ValueError", "exception": e}
	except urllib.error.URLError as e:
		return {"error": "URLError", "exception": e}

# Gets maze metadata in JSON from the API
def get_maze_state(maze_id):
	req = urllib.request.Request(api_calls["get_maze"].format(maze_id))
	response = urllib.request.urlopen(req)
	return json.loads(response.read().decode("utf-8"))

# Gets the ASCII representation of a maze state from the API
def get_maze_ascii(maze_id):
	req = urllib.request.Request(api_calls["print_maze"].format(maze_id))
	response = urllib.request.urlopen(req)
	return response.read().decode("utf-8")

# Sends an HTTP request to move the player
def move_player(direction, maze_id):
	if(direction not in valid_directions):
		print("Invalid direction: " + direction)
	else:
		payload = { "direction": direction }
		payload_json = json.dumps(payload).encode("utf-8")
		req = urllib.request.Request(api_calls["get_maze"].format(maze_id), data=payload_json, headers={'Content-Type': 'application/json'})
		response = urllib.request.urlopen(req)
		json_response = json.loads(response.read().decode("utf-8"))
		return(json_response)

# Clear console
def clear():
	if os.name in ('nt','dos'):
		subprocess.call("cls", shell=True)
	elif os.name in ('linux','osx','posix'):
		subprocess.call("clear", shell=True)
	else:
		print("\n"*120)

# Main path finding method. Finds the exit based on distance, previous positions and player trail
def find_path_to_exit(maze_id):

	# Returns a list of all positions and their distance to the exit
	def get_maze_catalog(maze):
		catalog = []
		for y in range(0, maze_height):
			for x in range(0, maze_width):
				end_point_x = int(maze["end-point"][0]) % maze_width
				end_point_y = int(int(maze["end-point"][0] - end_point_x) / maze_width)
				catalog.append(math.sqrt((x - end_point_x)**2 + (y - end_point_y)**2))
		return catalog

	# Returns a vector representation of a maze index
	def index_to_vector(index):
		return {
			"x": int(index % maze_width),
			"y": int(int(index - index % maze_width) / maze_width) % maze_height
		}

	# Loop related variables
	maze = get_maze_state(maze_id)
	catalog = get_maze_catalog(maze)
	player_trail = [0] * (maze_width * maze_height)
	old_domokun_index = -1
	j = 0
	cont_loop = True

	# PF loop
	while cont_loop:
		# Decrement player trail values; recent cells should have a higher penalty associated with moving on them
		for i in range(0, len(player_trail)):
			if player_trail[i] > 0:
				player_trail[i] -= 1

		# Variable declarations
		maze = get_maze_state(maze_id)
		player_x = int((maze["pony"][0]) % maze_width)
		player_y = int(int(maze["pony"][0] - player_x) / maze_width)
		domokun_x = int(maze["domokun"][0]) % maze_width
		domokun_y = int(int(maze["domokun"][0] - domokun_x) / maze_width)
		end_point_x = int(maze["end-point"][0]) % maze_width
		end_point_y = int(int(maze["end-point"][0] - end_point_x) / maze_width)
		
		# Explore the current options for moving the player
		current_options = maze["data"][player_x + player_y * maze_width]
		try:
			options_right = maze["data"][(player_x + 1) + player_y * maze_width]
		except IndexError as e:
			options_right = []
		try:
			options_bottom = maze["data"][player_x + (player_y + 1) * maze_width]
		except IndexError as e:
			options_bottom = []

		# Get indecies of the neighboring tiles
		top_index = index_to_vector((player_x + 0) + (player_y - 1) * maze_width)
		bot_index = index_to_vector((player_x + 0) + (player_y + 1) * maze_width)
		lef_index = index_to_vector((player_x - 1) + (player_y + 0) * maze_width)
		rig_index = index_to_vector((player_x + 1) + (player_y + 0) * maze_width)

		# Assign an 'impossibly' high number to walled section, discouraging the AI from wanting to move there
		top_node_dist = 9998 if "north" in current_options or top_index["y"] < 0 else catalog[top_index["x"] + top_index["y"] * maze_width]
		bot_node_dist = 9998 if "north" in options_bottom or bot_index["y"] >= maze_height else catalog[bot_index["x"] + bot_index["y"] * maze_width]
		lef_node_dist = 9998 if "west" in current_options or lef_index["x"] < 0 else catalog[lef_index["x"] + lef_index["y"] * maze_width]
		rig_node_dist = 9998 if "west" in options_right or rig_index["x"] >= maze_width else catalog[rig_index["x"] + rig_index["y"] * maze_width]

		# Assign a minor pentalty for moving in the same spot repeatedly encouraging exploration of new areas
		# This should always significantly be lower than the penalty for moving onto the monster, since
		# moving in the same spot for a while is more desireable, than moving onto the monster
		player_trail[player_x + player_y * maze_width] = 100


		# Assign ridiculous penalties to avaliable monster moves.
		domokun_options = []
		try:
			if "north" not in maze["data"][domokun_x + domokun_y * maze_width]:
				domokun_options.append("north")
		except IndexError:
			pass
		try:
			if "west" not in maze["data"][domokun_x + domokun_y * maze_width]:
				domokun_options.append("west")
		except IndexError:
			pass
		try:
			if "west" not in maze["data"][(domokun_x + 1) + domokun_y * maze_width]:
				domokun_options.append("east")
		except IndexError:
			pass
		try:
			if "north" not in maze["data"][domokun_x + (domokun_y + 1) * maze_width]:
				domokun_options.append("south")
		except IndexError:
			pass

		# Find avaliable moves for the monster, and assign penalties for moving to those locations.
		# Will in almost all cases prevent collision between the monster and the player
		# Exceptions include situations where the only escape path is blocked by the monster
		domokun_affected_tiles = []
		if "north" in domokun_options:
			domokun_affected_tiles.append((domokun_x + 0) + (domokun_y - 1) * maze_width)
		if "west" in domokun_options:
			domokun_affected_tiles.append((domokun_x - 1) + (domokun_y + 0) * maze_width)
		if "east" in domokun_options:
			domokun_affected_tiles.append((domokun_x + 1) + (domokun_y + 0) * maze_width)
		if "south" in domokun_options:
			domokun_affected_tiles.append((domokun_x + 0) + (domokun_y + 1) * maze_width)

		# Storing the old position so we can remove the penalty once the monster moves
		if old_domokun_index > -1:
			player_trail[old_domokun_index] -= 999998
			for index in old_domokun_affected_tiles:
				player_trail[index] -= 999997
		old_domokun_index = domokun_x + domokun_y * maze_width
		old_domokun_affected_tiles = domokun_affected_tiles

		# The penalty for moving onto/close to the monster should be 'impossibly' high
		player_trail[domokun_x + domokun_y * maze_width] = 999999
		for index in domokun_affected_tiles:
				player_trail[index] = 999998

		# Adjust for index out of bounds errors
		top_heat = 9998 if top_index["y"] < 0 				else player_trail[top_index["x"] + top_index["y"] * maze_width]
		bot_heat = 9998 if bot_index["y"] >= maze_height 	else player_trail[bot_index["x"] + bot_index["y"] * maze_width]
		lef_heat = 9998 if lef_index["x"] < 0 				else player_trail[lef_index["x"] + lef_index["y"] * maze_width]
		rig_heat = 9998 if rig_index["x"] >= maze_width 	else player_trail[rig_index["x"] + rig_index["y"] * maze_width]

		# Create a dictionary of the possible directions, sorts it based on the penalties then picks the 'cheapest' one
		directions = {
			"north": top_node_dist + top_heat,
			"south": bot_node_dist + bot_heat,
			"west": lef_node_dist + lef_heat,
			"east": rig_node_dist + rig_heat
		}
		direction = sorted(directions.items(), key=operator.itemgetter(1))[0][0]

		# Update the console with the progress
		sys.stdout.write("[{0:.2f}]\tSolving{1}\r".format(catalog[player_x + player_y * maze_width], spinner[j % 3]))
		sys.stdout.flush()

		# Send move request
		res = move_player(direction, maze_id)

		# Write maze state to replay files 
		open(base_path + "\\" + maze_id + "\\mazes\\{0}.txt".format(j), "w").write(get_maze_ascii(maze_id))

		j += 1
		cont_loop = player_x != end_point_x or player_y != end_point_y
		if res["state-result"] == "You lost. Killed by monster":
			break;
	print("Final result: " + res["state-result"])
	open(base_path + "\\" + maze_id + "\\final_result.txt", "w").write(res["state-result"])

if __name__ == "__main__":
	clear()
	if(not os.path.isdir(base_path)):
		os.mkdir(base_path)

	maze = create_maze()
	if(maze["error"] == ""):
		maze_id = maze["response"]
		print("Created maze with data " + maze_id)
		if(os.path.isdir(base_path + "\\" + maze_id)):
			print("Error: Maze with ID " + maze_id + " has already been processed")
			exit()
		else:
			os.mkdir(base_path + "\\" + maze_id)
			os.mkdir(base_path + "\\" + maze_id + "\\mazes")
		find_path_to_exit(maze_id)
	else:
		print(maze["error"] + " upon creating maze: " + str(maze["exception"]))