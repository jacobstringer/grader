"""Welcome to the quick marking script
Authored by Jacob Stringer
Call with 'python {filename}' to get further usage information"""

# Version 0.1.1

import os.path, os, re, sys, zipfile, io

# Global variables
sep = ';'
extracted = []

# Script functions
def create_file(dir):
    stp = re.compile(r'\w+ \w+_\d+_assignsubmission_file_')
    with open(f'{dir}/grades.csv', 'w') as f:
        f.write(f"sep={sep}\n")
        marks = []
        
        # Adds in titles
        f.write(input("What is the name of this paper? e.g. 'Intro to Programming': ") + ", " + input("Which assessment is this? e.g. 'Assignment 1': "))
        title = input("Write a title heading for a section you are marking, e.g. 'Depth First Search'. Write 'n' when done: ")
        while title.lower() != 'n':
            f.write(f"{sep}{title}{sep}")
            marks.append(input(f"How much is the grade for {title} worth? "))
            title = input("Write a title heading for a section you are marking, e.g. 'Depth First Search'. Write 'n' when done: ")
        f.write(f"{sep}Days Late{sep}General Comment")
        f.write("\n")
        
        # Adds in subtitles
        f.write("Subtitles")
        for mark in marks:
            f.write(f"{sep}Mark: {mark}{sep}Comment")
        f.write(f"{sep}" + input("How many % penalty is there per day late? "))
        f.write("\n")
        
        # Adds in student names
        for a in next(os.walk(dir))[1]:
            print(a)
            student = stp.findall(a)
            if student:
                f.write(student[0])
                f.write("\n")
            
            
def extract_nested_zip(toFolder, zippedFile = ""):
    global extracted
    print("Reached: ", toFolder)
    # Finds first zip file in folder, if none is specified
    if not zippedFile:
        for file in next(os.walk(toFolder))[2]:
            if re.search(r'\.(zip|rar)$', file) and file not in extracted:
                zippedFile = file
                break
    
    if zippedFile == "": return
    print("ZippedFile: ", zippedFile)
    total = os.path.join(toFolder, zippedFile)
	
    # Unzips file, checks for other files to unzip and makes a recursive call. Deletes original zip file.
    try:
        with zipfile.ZipFile(total, 'r') as zfile:
            zfile.extractall(path=toFolder)
            extracted.append(zippedFile)
        # os.remove(os.path.join(toFolder, zippedFile))
        for root, dirs, files in os.walk(toFolder):
            for filename in files:
                if re.search(r'\.(zip|rar)$', filename) and filename not in extracted:
                    #fileSpec = os.path.join(root, filename)
                    extract_nested_zip(root, filename)
    except Exception as e:
        print(e)
        

# Uses LaTeX for formatting, and then converts to PDF. Finally, deletes LaTeX file.
def print_to_pdf(outname, data):
    with open(outname, 'w') as out:
        # Preamble
        out.write(r"\documentclass{article}\n")
        out.write(r"\title{" + data[0] + "}\n")
        out.write(r"\author{" + data[1] + "}\n")

        # Document
        out.write(r"\begin{document}\n")
        out.write(r"\maketitle\n")
        for line in data[2:]:
            out.write(f"{line}\n")
        out.write(r"\end{document}\n")

        # Convert to PDF
        os.system(f"pdflatex {outname}")
        
    # Delete LaTeX file
    os.remove(outname)
    
      
def grade(dir):
    gradefile = open(f'{dir}/grades.csv', 'r').readlines()
    
    # Harvest titles and marks
    Titles = list(map(str.strip, gradefile[0].split(sep)))
    fullmarks = []
    for mark in gradefile[1].split(sep):
        if re.search(r'Mark:\s*\d+', mark, re.I):
            fullmarks.append(int(mark.split("Mark:")[1]))
    lateind = Titles.index("Days Late")
    generalind = Titles.index("General Comment")
    
    # For stats
    cumscore = 0
    nstudents = 0
    nstudentsabove20percent = 0
    cumscoreabove20percent = 0
    topmark = sum(fullmarks)
    percentile20 = topmark/5

    # Make marks folder for files. On later runs, any old files are cleaned up first.
    if not os.path.exists(f"{dir}/_marks"):
        os.mkdir(f"{dir}/_marks")
    else:
        for file in next(os.walk(f"{dir}/_marks"))[2]:
            os.remove(file)

    # Process marks
    for line in gradefile[2:]:
        line = list(map(str.strip, line.split(sep)))
        print(line)
        name = line[0]

        marks = 0
        msg = []
        msg.append(Titles[0]) # Paper name and assignment name
        msg.append(name.split("_")[0] + "\n") # First and last name of student
        
        # Process student marks
        for i in range(1, lateind):
            if i == 0: continue # Name
            if not line[i]: continue # Empty cell
            if Titles[i]:
                marks += int(line[i])
                msg.append(f'{Titles[i]}: {line[i]}/{fullmarks[i//2]}')
            else:
                msg.append(line[i] + "\n")

        # Late, General Comments and Marks
        marks = max(0, marks - int(line[lateind]) * int(gradefile[1][lateind]))
        msg.append(f'\nDue to being {line[lateind]} days late, a {int(line[lateind]) * int(gradefile[1][lateind])}% point penalty has been applied.')
        msg.append(f'\n{Titles[generalind]}: {line[generalind]}')
        
        marks = round(marks,1)
        msg.append(f'\nTotal mark: {marks}/{fullmarks}')
        
        # Create feedback file
        with open(f'{dir}/_marks/{line[0]}{line[0].split("_")[0]}_{marks}.txt', 'w') as out:
            msg = [i + "\n" for i in msg]
            out.writelines(msg)
        
        # Stats
        cumscore += marks
        nstudents += 1
        if marks > percentile20:
            cumscoreabove20percent += marks
            nstudentsabove20percent += 1
    
    # Zip feedback files
    with zipfile.ZipFile(f'{dir}/marks.zip', 'w') as zipout:
        for file in next(os.walk(f"{dir}/_marks"))[2]:
            zipout.write(file)
    
    print("Average mark: ", cumscore/nstudents)
    print("Average mark for those above 20%: ", cumscoreabove20percent/nstudentsabove20percent)

    
def help():
    print("""  
UNZIP - Recursively unzips all .zip files within the listed folder (or in the current dir)
python gradescript.py unzip <dir with zip file(s)>

CREATE - Creates file to start grading
python gradescript.py create <dir with unzipped student submissions>

GRADE
python gradescript.py grade <dir with grades.csv>
""")


"""
Welcome to the quick marking script! This script does all the grunt work for you, so you can focus on giving great feedback. It will unzip files, create a grading csv and then, when you are ready, it will create student feedback files and zip them up for quick upload on stream.

What you need to do for it to run:
1. Copy file into a folder with the zipped assignment submission (preferably ONLY this assignment, as it will unzip everything from the current working directory down).
2. Do not use semicolons in your comments when filling in the CSV file. If you wish to use semicolons, update the 'sep' global variable to another delimiter.

There are the following options (case insensitive):


CREATE (todo: unzipping for other file types apart from zip)
python gradescript.py create

This command will recursively unzip anything in the current working directory and any subfolders. It will then create grades.csv where you can add in grades and comments. Optionally you can add in grading titles and marks at this point, or you can add titles later yourself. The grade function follows the specific format, where late and general comments are the final columns (anything after this are ignored). An example of how to fill in the csv is given:
Col 1           Col 2
Title           (empty)
Mark: #         (anything)
2               This is a comment about this section.




This takes all the information you have added into your csv and creates feedback text files in the _marks folder. It also zips the feedback files to marks.zip, which can be uploaded to stream. The feedback files include their names and marks, so that when using the quick mark function, you can quickly enter in marks.
"""
                

if __name__ == "__main__":
	if len(sys.argv) > 2:
		dir = sys.argv[2]
	else:
		dir = "."
		
	if not len(sys.argv) > 1 or sys.argv[1].lower() not in ["unzip", "create", "grade"]:
		help()
	elif sys.argv[1].lower() == "unzip":
		extract_nested_zip(dir)
	elif sys.argv[1].lower() == "create":
		create_file(dir)
	else:
		grade(dir)
