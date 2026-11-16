
import tkinter as tk
from queue import PriorityQueue
import heapq
import math

class Cell:
    #### Initially, all maze cells have g() = inf and h() = 0
    def __init__(self, x, y, is_wall=False):
        self.x = x
        self.y = y
        self.is_wall = is_wall
        self.g = float("inf")
        self.h = 0
        self.f = float("inf")
        self.parent = None

    #### Compare two cells based on their evaluation functions
    def __lt__(self, other):
        return self.f < other.f

class AStar_AP:
    def __init__(self, root, maze, priority_map):
        self.root = root
        self.maze = maze
        self.priority_map = priority_map
        self.rows = len(maze)
        self.cols = len(maze[0])
        inputfile = input("Enter Filename: " )
        self.linestr = []
        try:
            with open(inputfile, "r") as file:
                content = file.read()
                self.linestr = content.splitlines()
        except FileNotFoundError:
            print(f"FATAL ERROR: Input file not found at '{inputfile}'.")
            raise  # Re-raise the exception to stop initialization
            
        except Exception as e:
            # Catch other I/O errors (e.g., permission issues)
            print(f"FATAL ERROR: Failed to read input file: {e}")
            raise
        if not self.linestr:
            print("FATAL ERROR: Input file is empty.")
            raise ValueError("Input file must contain data.")
        if len(self.linestr) < 2:
            print("FATAL ERROR: Input file is missing start point (Line 2).")
            raise IndexError("Input file is too short.")
        self.pathfinder = self.linestr[0].strip()
        print(self.pathfinder)
        self.coordstr = []
        if self.linestr:
            thirdline = self.linestr[2].strip()
            self.coordstr = thirdline.split(" ")
        print(self.coordstr)
        delimiter = ","
        try:
            self.coords = [
                [int(num) for num in s.split(delimiter)] for s in self.coordstr
            ]
        except ValueError:
                print("FATAL ERROR: Delivery coordinates (Line 3) contains non-integer or malformed data.")
                raise  # Re-raise the ValueError with the descriptive message
        except Exception as e:
                print(f"FATAL ERROR during delivery coordinate parsing: {e}")
                raise
        print(self.coords)
        #### Start state: (0,0) or top left
        try:        
            secondline = self.linestr[1].strip()
            startpoint = secondline.split(",")
            self.agent_pos = [int(s) for s in startpoint]
        except ValueError:
            print("FATAL ERROR: Start point (Line 2) contains non-integer or malformed coordinates.")
            raise
        except Exception as e:
            print(f"FATAL ERROR during start point parsing: {e}")
            raise  
        # Boundary check
        if not (0 <= self.agent_pos[0] < self.rows and 0 <= self.agent_pos[1] < self.cols):
            print(f"FATAL ERROR: Starting position {self.agent_pos} is outside maze boundaries.")
            raise ValueError("Starting position out of bounds.")
            
        # Goal state: will be set dynamically
        self.goal_pos = None
        
        # Ward priority mapping as class attribute
        self.WARD_PRIORITY = {
            "ICU": 5, "ER": 5, "Oncology": 5, "Burn Ward": 5,
            "Surgical Ward": 4, "Maternity Ward": 4,
            "Hematology": 3, "Pediatric Ward": 3,
            "Medical Ward": 2, "General Ward": 2,
            "Admissions": 1, "Isolation Ward": 1,
            "Hallway": 1
        }
        
        # Map numeric codes to ward names
        self.CODE_TO_WARD = {
            1: "Hallway",
            2: "Isolation Ward",
            3: "Medical Ward",
            4: "Hematology", 
            5: "Maternity Ward",
            6: "ICU"
        }
        
        self.cells = [[Cell(x, y, maze[x][y] == 0) for y in range(self.cols)] for x in range(self.rows)]
        
        #### Start state's initial values for f(n) = g(n) + h(n) 
        self.cells[self.agent_pos[0]][self.agent_pos[1]].g = 0
        self.cells[self.agent_pos[0]][self.agent_pos[1]].h = 0
        self.cells[self.agent_pos[0]][self.agent_pos[1]].f = 0

        #### The maze cell size in pixels
        self.cell_size = 18
        self.canvas = tk.Canvas(root, width=self.cols * self.cell_size, height=self.rows * self.cell_size, bg='white')
        self.canvas.pack()

        # Store delivery requests and current path
        self.delivery_order = []
        self.current_delivery_index = 0
        self.current_path = []
        
        self.draw_maze()
        self.entry_box = tk.Entry(root, width=50)
        self.entry_box.pack(pady=5)
        
        self.button = tk.Button(root, text="Get Coordinates", command=self.get_entry_text)
        self.button.pack()        

    def change_wall(self, event):
        row = math.floor(event.y/98)
        col = math.floor(event.x/28)
        if self.maze[row][col] == 1:
            self.maze[row][col] = 0
            self.cells[row][col].is_wall = True
        else:
            self.maze[row][col] = 1
            self.cells[row][col].is_wall = False     
        self.canvas.itemconfig(f"Wall added at ({row}, {col})")
        self.draw_maze()
    
    def get_entry_text(self):
        text = self.entry_box.get()
        listext = text.split(",")
        self.newCoord = [int(s) for s in listext]
        print("Entered Coordinates:", self.newCoord) 
        self.coords.append(self.newCoord)   

    def manhattan_distance(self, pos1, pos2):
        # Calculate Manhattan distance between two positions
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


    def build_priority_queue(self, priority_map, start_point):
        # Build priority queue of delivery requests
        pq = []  # (priority_key, distance, counter, ward_name, point)
        counter = 0

        rows = len(self.coords)

        for r in range(rows):
            ward = (priority_map[self.coords[r][0]][self.coords[r][1]])

            # Skip empty / wall / no-request cells
            if ward is None:
                continue

            ward_priority = self.WARD_PRIORITY[ward]
            dist = self.manhattan_distance((self.coords[r][0],self.coords[r][1]), start_point)

            # Priority key: (-ward_priority, distance)
            #   → highest ward priority first
            #   → if same ward, closer cells first
            item = (-ward_priority, dist, counter, ward, (self.coords[r][0],self.coords[r][1]))
            heapq.heappush(pq, item)
            counter += 1
        
        return pq
    

    def process_requests(self, pq):
        # Process delivery requests according to priority rules
        result_order = []
        current_ward = None
        
        if not pq:
            print("WARNING: No delivery requests were successfully built. Exiting processing.")
            return result_order
        
        while pq:
                # If robot is already in a ward and more tasks remain in that ward:
                if current_ward is not None:
                    same_ward_items = []
                    temp = []
    
                    # Extract all items and separate ones in this ward
                    while pq:
                        try:
                            item = heapq.heappop(pq)
                            if item[3] == current_ward:
                                same_ward_items.append(item)
                            else:
                                temp.append(item)
                        except IndexError:
                            print(f"ERROR: Corrupt data found in priority queue item: {item}. Skipping.")
                            continue
    
                    # Restore the others
                    for t in temp:
                        heapq.heappush(pq, t)
    
                    # If tasks in same ward exist → finish them all
                    if same_ward_items:
                        try:
                            for _, _, _, ward, point in sorted(same_ward_items, key=lambda x: x[1]):
                                result_order.append(("deliver", ward, point))
                            continue  # Continue loop and check again
                        except TypeError:
                            print("ERROR: Priority queue item structure is invalid (cannot sort/unpack). Stopping processing.")
                            return result_order
    
                # Otherwise pull the next highest-priority request
                try:
                    _, _, _, ward, point = heapq.heappop(pq)
                except IndexError:
                    print("ERROR: Corrupt data encountered when popping item from the priority queue. Stopping processing.")
                    break # Exit the while loop
    
                # Robot moves to a new ward
                if ward != current_ward:
                    current_ward = ward
                    result_order.append(("move_to", ward))
    
                result_order.append(("deliver", ward, point))
        return result_order


    def setup_delivery_system(self):
        # Convert priority_map to ward names and setup delivery queue
        # Convert priority_map numbers to ward names
        ward_map = []
        for row in range(self.rows):
            ward_row = []
            for col in range(self.cols):
                code = self.priority_map[row][col]
                if code in self.CODE_TO_WARD:
                    ward_row.append(self.CODE_TO_WARD[code])
                else:
                    ward_row.append(None)
            ward_map.append(ward_row)
        
        # Build priority queue
        pq = self.build_priority_queue(ward_map, self.agent_pos)
        
        # Get delivery order
        self.delivery_order = self.process_requests(pq)
        
        # Print delivery order for debugging
        print("\n=== DELIVERY ORDER ===")
        for i, order in enumerate(self.delivery_order):
            if order[0] == "move_to":
                print(f"{i}. Move to ward: {order[1]}")
            else:
                print(f"{i}. Deliver to {order[1]} at position {order[2]}")
        print("======================\n")
        
        # Start first delivery
        if self.delivery_order:
            self.execute_next_delivery()


    def execute_next_delivery(self):
        # Execute the next delivery in the queue
        if self.current_delivery_index >= len(self.delivery_order):
            self.reset_search()
            self.current_delivery_index = 0
            print("All deliveries completed!")
            return
        
        current_order = self.delivery_order[self.current_delivery_index]
        
        if current_order[0] == "move_to":
            # Just log the ward change, immediately process next
            print(f"Moving to ward: {current_order[1]}")
            self.current_delivery_index += 1
            self.execute_next_delivery()
        else:
            # Deliver action - find path to destination
            action, ward, destination = current_order
            print(f"Planning route to {ward} at {destination}")
            self.goal_pos = destination
            self.find_path_to_goal()


    def find_path_to_goal(self):
        # Find A* path from current position to goal
        self.reset_search()
        
        open_set = PriorityQueue()
        
        #### Add the start state to the queue
        start_pos = self.agent_pos
        open_set.put((0, start_pos))
        
        #### Check for pathfinder
        valid_pathfinders = {"A*", "Dijkstra"}
        if self.pathfinder not in valid_pathfinders:
            error_msg = f"Invalid pathfinder specified: '{self.pathfinder}'. Must be one of {', '.join(valid_pathfinders)}."
            print(f"FATAL ERROR: {error_msg}")
            # Raise a specific error to immediately halt execution of this function.
            raise ValueError(error_msg)

        #### Continue exploring until the queue is exhausted
        while not open_set.empty():
            current_cost, current_pos = open_set.get()
            current_cell = self.cells[current_pos[0]][current_pos[1]]

            #### Stop if goal is reached
            if current_pos == self.goal_pos:
                self.reconstruct_path()
                return
            
            #### Agent goes E, W, N, and S, whenever possible
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_pos = (current_pos[0] + dx, current_pos[1] + dy)

                if 0 <= new_pos[0] < self.rows and 0 <= new_pos[1] < self.cols and not self.cells[new_pos[0]][new_pos[1]].is_wall:
                
                    #### The cost of moving to a new position is 1 unit
                    new_g = current_cell.g + 1
                    
                    if new_g < self.cells[new_pos[0]][new_pos[1]].g:
                        ### Update the path cost g()
                        self.cells[new_pos[0]][new_pos[1]].g = new_g
                        
                        ### Update the heuristic h()
                        if self.pathfinder == "A*":
                            self.cells[new_pos[0]][new_pos[1]].h = self.heuristic(new_pos)
                        elif self.pathfinder == "Dijkstra":
                            self.cells[new_pos[0]][new_pos[1]].h = 0
                        # Error handling for invalid pathfinding algorithm in file
                        else:
                            print("Error: Invalid pathfinding algorithm specified.")
                            print("Please specify either 'A*' or 'Dijkstra' in the input file.")
                            break
                        
                        ### Update the evaluation function for the cell n: f(n) = g(n) + h(n)
                        self.cells[new_pos[0]][new_pos[1]].f = new_g + self.cells[new_pos[0]][new_pos[1]].h
                        self.cells[new_pos[0]][new_pos[1]].parent = current_cell
                        
                        #### Add the new cell to the priority queue
                        open_set.put((self.cells[new_pos[0]][new_pos[1]].f, new_pos))
        print(f"WARNING: Pathfinding failed. Goal position {self.goal_pos} is unreachable from {self.agent_pos}.")
            
    def heuristic(self, pos):
        # Manhattan distance heuristic
        if self.goal_pos is None:
            return 0
        return self.manhattan_distance(pos, self.goal_pos)


    def reconstruct_path(self):
        # Reconstruct path from start to goal
        self.draw_maze()
        
        # Build the full list of cells in the final path
        path = []
        current_cell = self.cells[self.goal_pos[0]][self.goal_pos[1]]

        while current_cell.parent:
            path.append(current_cell)
            current_cell = current_cell.parent

        path.reverse()  # Starts at start
        
        self.current_path = path

        # Animate the path
        self.animate_path(path)


    def animate_path(self, path, index=0):
        # Animate the path step by step
        if index >= len(path):
            # Path complete, move to next delivery
            self.agent_pos = self.goal_pos
            self.current_delivery_index += 1
            
            # Wait before next delivery
            self.root.after(1000, self.execute_next_delivery)
            return
        
        cell = path[index]
        x, y = cell.x, cell.y
        
        # Draw the path cell
        self.canvas.create_rectangle(
            y * self.cell_size, x * self.cell_size,
            (y + 1) * self.cell_size, (x + 1) * self.cell_size,
            fill='slateblue1', tags="path"
        )

        # Display the g/h values
        text = f'g={self.cells[x][y].g}\nh={self.cells[x][y].h}'
        self.canvas.create_text(
            (y + 0.5) * self.cell_size,
            (x + 0.5) * self.cell_size,
            font=("Purisa", 4),
            text=text
        )
        
        if index + 1 >= len(path):
            # Final destination - mark as completed
            self.canvas.create_rectangle(
                y * self.cell_size, x * self.cell_size,
                (y + 1) * self.cell_size, (x + 1) * self.cell_size,
                fill='springgreen'
            )

            text = f'g={self.cells[x][y].g}\nh={self.cells[x][y].h}'
            self.canvas.create_text(
                (y + 0.5) * self.cell_size,
                (x + 0.5) * self.cell_size,
                font=("Purisa", 4),
                text=text
            )
        
        # Schedule drawing the next cell after 50 milliseconds
        self.root.after(75, lambda: self.animate_path(path, index + 1))
        


    def draw_maze(self):
        for x in range(self.rows):
            for y in range(self.cols):
                if self.priority_map[x][y] == 3:
                    color = 'gray30'
                elif self.priority_map[x][y] == 0:
                    color = 'gray63'
                elif self.priority_map[x][y] == 2:
                    color = 'red'
                elif self.priority_map[x][y] == 1:
                    color = 'gold'
                elif self.priority_map[x][y] == 4:
                    color = 'deepskyblue'
                elif self.priority_map[x][y] == 5:
                    color = 'magenta2'
                else:
                    color = 'white'
                    
                self.canvas.create_rectangle(
                    y * self.cell_size, x * self.cell_size, 
                    (y + 1) * self.cell_size, (x + 1) * self.cell_size, 
                    fill=color
                )
                
                if not self.cells[x][y].is_wall:
                    text = f'g={self.cells[x][y].g}\nh={self.cells[x][y].h}'
                    self.canvas.create_text(
                        (y + 0.5) * self.cell_size, 
                        (x + 0.5) * self.cell_size, 
                        font=("Purisa", 4), 
                        text=text
                    )
                    
        # Draw agent
        self.canvas.create_rectangle(
            self.agent_pos[1] * self.cell_size, 
            self.agent_pos[0] * self.cell_size, 
            (self.agent_pos[1] + 1) * self.cell_size, 
            (self.agent_pos[0] + 1) * self.cell_size, 
            fill='blue2', 
            tags="agent"
        )


    def reset_search(self):
        # Reset all cell values for new search
        for x in range(self.rows):
            for y in range(self.cols):
                cell = self.cells[x][y]
                cell.g = float("inf")
                cell.h = 0
                cell.f = float("inf")
                cell.parent = None

        # Reset start cell
        start_cell = self.cells[self.agent_pos[0]][self.agent_pos[1]]
        start_cell.g = 0
        start_cell.h = self.heuristic(self.agent_pos)
        start_cell.f = start_cell.h
        self.coords.clear()
        # Clear the canvas and redraw the maze
        self.canvas.delete("all")
        self.draw_maze()


    def move_agent(self, event):
        # Manual agent movement (for testing)
        # Move right, if possible
        if event.keysym == 'Right' and self.agent_pos[1] + 1 < self.cols and not self.cells[self.agent_pos[0]][self.agent_pos[1] + 1].is_wall:
            self.agent_pos = (self.agent_pos[0], self.agent_pos[1] + 1)

        # Move Left, if possible            
        elif event.keysym == 'Left' and self.agent_pos[1] - 1 >= 0 and not self.cells[self.agent_pos[0]][self.agent_pos[1] - 1].is_wall:
            self.agent_pos = (self.agent_pos[0], self.agent_pos[1] - 1)
        
        # Move Down, if possible
        elif event.keysym == 'Down' and self.agent_pos[0] + 1 < self.rows and not self.cells[self.agent_pos[0] + 1][self.agent_pos[1]].is_wall:
            self.agent_pos = (self.agent_pos[0] + 1, self.agent_pos[1])
   
        # Move Up, if possible   
        elif event.keysym == 'Up' and self.agent_pos[0] - 1 >= 0 and not self.cells[self.agent_pos[0] - 1][self.agent_pos[1]].is_wall:
            self.agent_pos = (self.agent_pos[0] - 1, self.agent_pos[1])
        # Setup and execute delivery system
        elif event.keysym == 'Tab':
            self.setup_delivery_system()
        
        # Erase agent from the previous cell at time t
        self.canvas.delete("agent")
        
        # Redraw the agent in color navy in the new cell position at time t+1
        self.canvas.create_rectangle(
            self.agent_pos[1] * self.cell_size, 
            self.agent_pos[0] * self.cell_size, 
            (self.agent_pos[1] + 1) * self.cell_size, 
            (self.agent_pos[0] + 1) * self.cell_size, 
            fill='blue2', 
            tags="agent"
        )  
        
        
        

                  

############################################################
#### Modify the wall cells to experiment with different maze
#### configurations.
############################################################
map = [
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,1,0,1,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,1,0,0,0,0,0,1,1,0,0,0,1,1,0,0,0,1,0,0,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,0,1,0,1,0,1,0,1,0,0,0,1,0,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,0,0,1],
     [1,1,1,0,0,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,1,0,1,0,1,1,1,0,1,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,0,1,1],
     [1,1,0,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,0,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1,0,1,1,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,0,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1,0,1,1,1,1,1,1,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,1,0,1,1,1,1,1,1,0,1,0,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,0,1,1,1,1,1,1,0,1,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,0,0,1,0,1,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,0,0,1,0,0,1,0,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0,1,1,1,0,1,1,1,1,0,1,1,1,0,1,0,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,0,1,0,1,1,0,0,1,0,0,0,1,0,1,0,0,0,1,1,1,1,0,1,0,0,0,1,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,1,0,0,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,0,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,1,0,0,1,1,1,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,1,1,1,1,1,0,0,0,0,1,0,1,0,1,0,1,1,1,1,0,1,0,0,0,0,1,0,1,0,0,1,0,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,1,1,1,0,0,0,1,1,1,1,0,1,0,1,0,1,1,1,1,0,1,1,1,0,1,1,1,1,1,0,1,0,1,0,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]
priority_map = [
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,1,0,1,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,1,0,0,0,0,0,1,1,0,0,0,1,1,0,0,0,1,0,0,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1],
     [1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,0,1,0,1,0,1,0,1,0,0,0,1,0,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,0,0,1],
     [1,1,1,0,0,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,1,0,1,0,1,1,1,0,1,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,0,1,1],
     [1,1,0,0,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,0,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1,0,1,1,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,0,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1,0,1,1,1,1,1,1,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1],
     [1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,1,0,1,1,1,1,1,1,0,1,0,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1],
     [1,0,1,1,1,1,1,1,0,1,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,0,0,1,0,1,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,0,0,1,0,0,1,0,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0,1,1,1,0,1,1,1,1,0,1,1,1,0,1,0,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,0,1,0,1,1,0,0,1,0,0,0,1,0,1,0,0,0,1,1,1,1,0,1,0,0,0,1,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,1,0,0,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,0,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,1,0,0,1,1,1,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,1,1,1,1,1,0,0,0,0,1,0,1,0,1,0,1,1,1,1,0,1,0,0,0,0,1,0,1,0,0,1,0,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,1,1,1,1,1,1,0,0,0,1,1,1,1,0,1,0,1,0,1,1,1,1,0,1,1,1,0,1,1,1,1,1,0,1,0,1,0,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
     [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]

############################################################
#### The mainloop activates the GUI.
############################################################
root = tk.Tk()
root.title("A* AccessPath")

game = AStar_AP(root, map, priority_map)
root.bind("<KeyPress>", game.move_agent)
root.bind("<Button-1>", game.change_wall)

root.mainloop()