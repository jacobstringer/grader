"""Welcome to the quick marking script
Authored by Jacob Stringer
Call with 'python {filename}' to get further usage information"""

# Version 0.3.0 - Implements the functionality for creating PDFs (via Latex)
# Version 0.2.0 - Includes options to create a grading file for a subset of (first) names. Deletes other files.
# Version 0.1.1 - Got the recursive unzipping (for .zip files) working

import os.path, os, re, sys, zipfile, csv

# Global variables
sep = ','
firstExtracted = None
ignore = []
filesUnzipped = 0


# Script functions
def create_file(dir, first = None, last = None):
    stp = re.compile(r'.+_\d+_assignsubmission_file_')
    comment = re.compile(r'.+_\d+_assignsubmission_onlinetext_')
    with open(f'{dir}/grades.csv', 'w') as f:
        f.write(f"sep={sep}\n")
        marks = []

        # Adds in titles
        f.write(input("What is the name of this paper? e.g. '158.100': ") + ": " + input(
            "Which assessment is this? e.g. 'Assignment 1': "))
        title = input(
            "Write a title heading for a section you are marking, e.g. 'Depth First Search'. Write 'n' when done: ")
        while title.lower() != 'n':
            f.write(f"{sep}{title}{sep}")
            marks.append(input(f"How much is the grade for {title} worth? "))
            title = input(
                "Write a title heading for a section you are marking, e.g. 'Depth First Search'. Write 'n' when done: ")
        f.write(f"{sep}Days Late{sep}General Comment")
        f.write("\n")

        # Adds in subtitles
        f.write("Subtitles")
        for mark in marks:
            f.write(f"{sep}Mark: {mark}{sep}Comment")
        f.write(f"{sep}" + input("How many % penalty is there per day late? "))
        f.write("\n")

        # Adds in student names
        root, folders, files = next(os.walk(dir))
        students = []
        for a in folders+files:
            student = stp.findall(a)
            if student:
                if student[0] not in students:
                    if not first or not last or first <= student[0].split(" ")[0].lower() <= last:
                        students.append(student[0])

            # Remove files that aren't needed (if a student range is specified)
            if first and last and not first <= a.split(" ")[0].lower() <= last and (student or comment.findall(a)):
                try:
                    if os.path.isdir(a):
                        os.rmdir(a)
                    elif os.path.isfile(a):
                        os.remove(a)
                except Exception as e:
                    print(e)

        f.write("\n".join(sorted(students, key=lambda x: x.lower())))


def extract_nested_zip(folder):
    global filesUnzipped, firstExtracted, ignore
    for root, dirs, files in os.walk(folder):
        for file in files:
            subfolder = os.path.join(root, file[:-4])
            path = os.path.join(root, file)

            if file.endswith(".zip") and file not in ignore:
                try:
                    with zipfile.ZipFile(path, 'r') as zfile:
                        zfile.extractall(path=subfolder)
                        filesUnzipped += 1
                    if firstExtracted:
                        os.remove(os.path.join(root, file))
                    else:
                        firstExtracted = file
                        ignore.append(firstExtracted)  # Do not remove the original zip file
                    return extract_nested_zip(root)  # In order to recursively unzip files, must restart os.walk

                except Exception as e:
                    ignore.append(file)
                    print(e)


# Uses LaTeX for formatting, and then converts to PDF. Finally, deletes LaTeX file.
def print_to_pdf(outname, data):
    # data = list(map(str.strip, data))
    os.chdir("./_marks")

    with open(outname, 'w') as out:
        # Preamble
        out.write(f"""\\documentclass{{report}}
\\begin{{document}}
\\section*{{{data[0]}}}
\\subsection*{{{data[1]}}}""")

        for line in data[2:]:
            out.write(f"{line}\\newline{{}}")
        out.write(r"\end{document}" + "\n")

    # Convert to PDF
    os.system(f'pdflatex "{outname}"')

    # Delete LaTeX file
    os.remove(outname)
    os.remove(outname.replace(".tex", ".aux"))
    os.remove(outname.replace(".tex", ".log"))
    os.chdir("..")


def grade(dir, pdf):
    # For stats
    scores = []

    # Make marks folder for files. On later runs, any old files are cleaned up first.
    if not os.path.exists(f"{dir}/_marks"):
        os.mkdir(f"{dir}/_marks")
    else:
        root, b, files = next(os.walk(f"{dir}/_marks"))
        for file in files:
            os.remove(os.path.join(root, file))

    # Get file
    gradefile = open(f'{dir}/grades.csv', 'r').readlines()
    with open(f'{dir}/grades.csv', 'r') as csvFile:
        csvData = csv.reader(csvFile)
        lineNum = -1

        # Process data
        for line in csvData:
            lineNum += 1
            # Get titles
            if lineNum == 0:
                titles = line
                lateind = titles.index("Days Late")
                generalind = titles.index("General Comment")

            # Get marks information
            elif lineNum == 1:
                fullmarks = []
                for mark in gradefile[1].split(sep):
                    if re.search(r'Mark:\s*\d+', mark, re.I):
                        fullmarks.append(int(mark.split("Mark:")[1]))
                late_penalty_per_day = int(line[lateind])
                highest_score = sum(fullmarks)

            # Process each line
            else:
                name_and_submission = line[0]
                if name_and_submission == "".join(line):
                    print("Skipping {} due to no information".format(name_and_submission))
                    continue

                marks = 0
                msg = [titles[0], name_and_submission.split("_")[0]]

                # Process student marks
                for i in range(1, lateind):
                    if titles[i]:  # Marked column
                        if not line[i]:  # Empty cell
                            print("Warning: {} has no mark for {}".format(name_and_submission, titles[i]))
                            msg.append(f'{titles[i]}: 0/{fullmarks[i // 2]}')
                            msg.append("Missing")
                        else:
                            marks += float(line[i])
                            msg.append(f'{titles[i]}: {line[i]}/{fullmarks[i // 2]}')
                    else:  # Comment column
                        msg.append(line[i])
                        if line[i]:
                            msg.append("")

                # Late, General Comments and Marks
                if line[lateind] and float(line[lateind]) > 0:
                    marks = max(0, marks - float(line[lateind]) * late_penalty_per_day)
                    msg.append(f'Due to being {line[lateind]} days late, a {float(line[lateind]) * late_penalty_per_day}% point penalty has been applied.')
                    msg.append("")
                if line[generalind]:
                    msg.append(titles[generalind])
                    msg.append(line[generalind])
                    msg.append("")

                
                if abs(marks - round(marks,0)) < 0.01:
                    marks = int(marks)
                else:
                    marks = round(marks, 1)
                msg.append(f'Total mark: {marks}/{highest_score}')

                # Create feedback file
                if pdf:
                    outfile = f'{line[0]}{line[0].split("_")[0]}_{marks}.tex'
                    print_to_pdf(outfile, msg)
                else:
                    outfile = f'{dir}/_marks/{line[0]}{line[0].split("_")[0]}_{marks}.txt'
                    with open(outfile, 'w') as out:
                        msg = [i + "\n" for i in msg]
                        out.writelines(msg)

                # Stats
                scores.append(marks)

    # Zip feedback files
    os.chdir("./_marks")
    root, b, files = next(os.walk("."))
    with zipfile.ZipFile('marks.zip', 'w') as zipout:
        for file in files:
            zipout.write(file)
    os.chdir("..")

    # Statistics
    print(f"Average mark: {sum(scores) / len(scores):0.2}\tAs percentage: {int(sum(scores) / len(scores) * 100 / highest_score)}%")
    print(f"Number of students below 50%: {len([x for x in scores if x/highest_score < 0.5])}/{len(scores)}")


def help():
    print("""  
UNZIP - Recursively unzips all .zip files within the listed folder (or in the current dir).
python grader.py unzip <dir with zip file(s)>

CREATE - Creates file to start grading. Includes an option to specify starting and ending first names (if splitting marking). Will delete files outside that range.
python grader.py create <dir with unzipped student submissions>

GRADE
python grader.py grade <dir with grades.csv>
""")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        directory = sys.argv[2]
    else:
        directory = "."

    os.chdir(directory)
    if not len(sys.argv) > 1 or sys.argv[1].lower() not in ["unzip", "create", "grade"]:
        help()
    elif sys.argv[1].lower() == "unzip":
        extract_nested_zip(directory)
        print(f"{filesUnzipped} files unzipped!")
    elif sys.argv[1].lower() == "create":
        if input("Are you marking the entire set? (y/n)").lower() == "n":
            first = input("Please enter the first name you are marking: ").lower()
            last = input("Please enter the last name you are marking: ").lower()
            create_file(directory, first, last)
        else:
            create_file(directory)
    else:
        while True:
            pdf = input("Do you wish to print PDFs? You must have a Latex distribution installed (y or n):").lower()
            if pdf == 'y':
                pdf = True
                break
            elif pdf == 'n':
                pdf = False
                break
        grade(directory, pdf)
