import os
import sys

class edge:
    src = dst = wgt = 0

    def __init__(self, source, dest, w):
        self.src = source
        self.dst = dest
        self.wgt = w

    def get_edge_repr(self):
        return "({},{})".format(self.src, self.dst)

    def __str__(self):
        return " [{},{}] {}".format(self.src, self.dst, self.wgt)

    def __repr__(self):
        return " [{},{}] {}".format(self.src, self.dst, self.wgt)

# grafy bez kratkych cyklov
def generate(path, filename, compute, compute_destination="", multi_run=False):
    edges = list()

    node_count = 1
    with open(path + filename, 'r') as file:
        lines = file.readlines()
        node_count = int(lines[0].split()[2].strip())
        for i in range(1, len(lines)):
            elements = lines[i].strip().split()
            source_vertex = int(elements[0])
            destination_vertex = int(elements[2])
            weight = int(elements[4][:-1])
            edges.append(edge(source_vertex, destination_vertex, weight))
    edges_data = "".join([str(edges[i]) for i in range(len(edges))])

    edge_strings = []
    for e in edges:
        edge_strings.append(e.get_edge_repr())

    program_filename = "vygenerovane_lp.mod"
    if multi_run:
        program_filename = "vygenerovane_lp_" + filename[:filename.find(".")] + ".mod"

    with open(program_filename, 'w') as output_file:
        output_file.write('''set Nodes := 0..{};
set Edges := {{{}}};
param Weights{{(i,j) in Edges}};
var Removed{{(i,j) in Edges}}, binary;

minimize removedWeight: sum{{(i,j) in Edges}} Weights[i,j] * Removed[i,j];
s.t. noThreeCycle{{i in Nodes, j in Nodes, k in Nodes: i!=j and j!=k and k!=i}}:
  (if ((i,j) in Edges and (j,k) in Edges and (k,i) in Edges) then (Removed[i,j] + Removed[j,k] + Removed[k,i]) else 1) >= 1;
s.t. noFourCycle{{i in Nodes, j in Nodes, k in Nodes, l in Nodes: i!=j and j!=k and k!=l and l!=i}}:
  (if ((i,j) in Edges and (j,k) in Edges and (k,l) in Edges and (l,i) in Edges) then (Removed[i,j] + Removed[j,k] + Removed[k,l] + Removed[l,i]) else 1) >= 1;

solve;

printf "#OUTPUT: %d\\n", sum{{(i,j) in Edges}} Weights[i,j] * Removed[i,j];
printf{{(i,j) in Edges}} (if Removed[i,j] then "%d --> %d\\n" else ""), i, j;
printf "#OUTPUT END\\n";

data;
param Weights {};
end;'''.format(node_count-1, ",".join(edge_strings), edges_data))
    if compute:
        os.system("glpsol -m {} >> {}".format(program_filename, compute_destination + filename))


# kocourkovske volby
def generate2(path, filename, compute, compute_destination="", multi_run=False):
    voters = []
    inverted = False

    with open(path + filename, 'r') as file:
        lines = file.readlines()
        entries = int(lines[0].strip().split()[1])
        edge_count = int(lines[0].strip().split()[2][:-1])
        if entries*(entries-1) < edge_count * 2:
            inverted = True
            for i in range(entries):
                voters.append(set([j for j in range(entries)]))
                voters[i].discard(i)

            for i in range(1, len(lines)):
                elements = lines[i].strip().split()
                source_vertex = int(elements[0])
                destination_vertex = int(elements[2])
                voters[source_vertex].discard(destination_vertex)
                voters[destination_vertex].discard(source_vertex)

        else:
            for i in range(entries):
                voters.append(set())

            for i in range(1, len(lines)):
                elements = lines[i].strip().split()
                source_vertex = int(elements[0])
                destination_vertex = int(elements[2])
                voters[source_vertex].add(destination_vertex)
                voters[destination_vertex].add(source_vertex)

    voters_size = len(voters)
    strings = []
    for i in range(voters_size):
        for element in voters[i]:
            strings.append("({},{})".format(i, element))
    edges = ",".join(strings)

    # avoid empty 1-dimensional list (when graph is complete)
    if edges == "":
        edges = "({},{})".format(voters_size, voters_size)

    program_filename = "vygenerovane_lp.mod"
    if multi_run:
        program_filename = "vygenerovane_lp_" + filename[:filename.find(".")] + ".mod"

    rule2 = ""
    if inverted:
        rule2 = '''s.t. twoColorEdge{{(i, j) in Edges, k in NodeIndexes}}:
NodeColor[i*N + k] + NodeColor[j*N + k] <= 1;'''
    else:
        rule2 = '''s.t. twoColorEdge{i in NodeIndexes, j in NodeIndexes, k in NodeIndexes: i!=j}:
(if (i,j) in Edges then 0 else (NodeColor[i*N + k] + NodeColor[j*N + k])) <= 1;'''

    with open(program_filename, 'w') as output_file:
        output_file.write('''param N := {};
set NodeIndexes := (0..N-1);
set Nodes := (0..N*N-1);
set Edges := {{{}}};
var Parties, >= 0, <= N-1, integer;
var NodeColor{{i in 0..N*N-1}}, binary;
minimize obj:Parties;
s.t. oneColor{{i in NodeIndexes}}:
sum{{j in NodeIndexes}} NodeColor[i*N + j] = 1;
{}
s.t. minZ{{i in NodeIndexes, j in NodeIndexes}}:
NodeColor[i*N + j] * j <= Parties;
solve;
printf "#OUTPUT: %d\\n", (Parties + 1);
printf{{i in 0..N*N-1}} (if NodeColor[i] = 1 then "v_%d: %d\\n" else ""), i div N, (i mod N);
printf "#OUTPUT END\\n";
end;'''.format(voters_size, edges, rule2))
    if compute:
        os.system("glpsol -m {} >> {}".format(program_filename, compute_destination + filename))


if len(sys.argv) > 5:
    option = sys.argv[1]
    path = sys.argv[2]
    filename = sys.argv[3]
    is_filelist = sys.argv[4]
    comp = False
    if sys.argv[5] == '-r':
        comp = True

    target_folder = path + "solutions/"
    if len(sys.argv) > 6:
        target_folder = sys.argv[6]

    if option != '1' and option != '2':
        print("Invalid option!")
        sys.exit(1)

    if is_filelist == '-y':
        with open(path + filename, 'r') as file:
            lines = file.readlines()
        for line in lines:
            tokens = line.split()
            filename = tokens[0].strip()
            if option == '2':
                filename = filename[:5] + filename[6:]
            expected = tokens[1].strip()

            if option == '1':
                generate(path, filename, comp, target_folder, True)
            else:
                generate2(path, filename, comp, target_folder, True)

            if comp:
                with open(target_folder + filename, 'r') as solution:
                    lines = solution.readlines()
                    index = -3
                    while lines[index][:8] != '#OUTPUT:':
                        index -= 1
                    target = lines[index]
                    result = target.split()[1].strip()
                    assert result == expected
                print("Successfully checked file", filename)
    else:
        if option == '1':
            generate(path, filename, comp)
        else:
            generate2(path, filename, comp)
