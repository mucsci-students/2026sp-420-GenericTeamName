"""
Lab Management System
Author: Mohamed Mussa
Course: CSCI 420
Description:
This program allows the user to display, add, remove, and modify lab sections
stored in a text file (section.txt).
"""


def menu():
    while(True):
        print()
        print("*************** Wellcome to Lab Mangment.  *************** ")
        print()
    
    
        print(
        
                "\nd : To Display Lab\n"
                "\na : To add Lab\n"
                "\nr : To remove Lab\n"
                "\nm : To modify Lab\n"
                "\nq : To quit\n"
             )
    
        choice = input("Enter option: ")
    
        match choice:
            case "d":
                display_lab()
            
            case "a":
                add_lab()
            case "r":
                remove_lab()
            case "m":
                 modifying_lab()
            case "q":
                print("Bye")
                break
            
            case _:
                print("Invalid option")
            
def display_lab():
    try:
        with open("section.txt", "r") as file:
            content =file.read()
            if content.strip() == "":
             print("No labs available.") 
             
            else:
                print("\n***** Lab Sections *****")
                print(content)
    except FileNotFoundError:
        print("No lab file found. Please add a lab frist.")
            
            
            
            
            
            
            
    
def add_lab():
    section = input("Enter section name: ")
    room = input("Enter room number: ")
    with open("section.txt", "a") as file:
        file.write(f"section: {section}\n")
        file.write(f"Room: {room}\n\n")
        
        
def remove_lab():
    section_to_remove = input("Enter the section name to remove: ").strip()

    with open("section.txt", "r") as file:
        lines = file.readlines()

    # Each lab entry is written as:
    # section: <name>
    # Room: <number>
    # (blank line)
    new_lines = []
    skip_block = False

    for line in lines:
        # Start skipping when we hit the matching section line
        if line.strip() == f"section: {section_to_remove}":
            skip_block = True
            continue

        # While skipping, skip the room line and the blank separator line too
        if skip_block:
            if line.startswith("Room:"):
                continue
            if line.strip() == "":
                skip_block = False
                continue
            # If formatting is unexpected, keep skipping until a blank line ends the block
            continue

        new_lines.append(line)

    with open("section.txt", "w") as file:
        file.writelines(new_lines)

    if len(new_lines) == len(lines):
        print("No matching section name was found.")
    else:
        print("Removed:", section_to_remove)
        
def section_exists(section_name):
    try:
        with open("section.txt", "r") as file:
            for line in file:
                if line.strip() == f"section: {section_name}":
                    return True
        return False
    except FileExistsError:
       return False
    
def modifying_lab():
    name_of_the_lab = input("Please Enter section name to modify: ").strip()

    if not section_exists(name_of_the_lab):
        print("Section not found.")
        return

    # Read all lines
    with open("section.txt", "r") as file:
        lines = file.readlines()

    # Find the section block
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == f"section: {name_of_the_lab}":
            start_idx = i
            break

    if start_idx is None:
        print("Section not found.")
        return

    section_line_idx = start_idx
    room_line_idx = start_idx + 1

    if room_line_idx >= len(lines) or not lines[room_line_idx].startswith("Room:"):
        print("File format error.")
        return

    current_room = lines[room_line_idx].strip().replace("Room:", "").strip()

    while True:
        print(
            "\nn  : Change section name\n"
            "r  : Change room number\n"
            "nr : Change both\n"
            "q  : Cancel\n"
        )

        choice = input("Please Enter: ").strip().lower()

        if choice == "q":
            print("Canceled.")
            return

        if choice not in {"n", "r", "nr"}:
            print("Invalid option.")
            continue

        new_name = name_of_the_lab
        new_room = current_room

        if choice in {"n", "nr"}:
            new_name = input("Enter new section name: ").strip()
            if new_name == "":
                print("Name cannot be empty.")
                continue

        if choice in {"r", "nr"}:
            new_room = input("Enter new room number: ").strip()
            if new_room == "":
                print("Room cannot be empty.")
                continue

        if new_name != name_of_the_lab and section_exists(new_name):
            print("Section name already exists.")
            continue

        lines[section_line_idx] = f"section: {new_name}\n"
        lines[room_line_idx] = f"Room: {new_room}\n"

        with open("section.txt", "w") as file:
            file.writelines(lines)

        print("Updated successfully!")
        return
    
if __name__ == "__main__":
    menu()