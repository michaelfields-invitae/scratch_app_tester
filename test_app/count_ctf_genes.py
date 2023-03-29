import argparse

from AMPPanelDesignLib.CTF import load_all_ctfs


def load_blacklist_primers(blacklist_file):
    blacklist = set()
    with open(blacklist_file, "r") as sr:
        for line in sr:
            blacklist.add(line.strip())
    return blacklist


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="CTF Gene Counter")
    parser.add_argument("-r", "--ctf-repository-folder", required=True, type=str, default=None,
                        help="Path to the folder containing CTF files.")
    parser.add_argument("-b", "--blacklist-primers-file", required=False, type=str, default=None,
                        help="Path to a file containing blacklisted primers that will not be included in the "
                             "final count.")
    parser.add_argument("-o", "--output-file", required=False, type=str, default=None,
                        help="OPTIONAL: Path to the output file where gene counts will be written."
                             "If no output file is provided, then gene counts will be written to STDOUT")

    args = parser.parse_args()
    ctf_folder = args.ctf_repository_folder
    blacklist_primers_file = args.blacklist_primers_file
    output_file = args.output_file

    ctf_list = load_all_ctfs(ctf_folder).values()
    blacklisted_primers = load_blacklist_primers(blacklist_primers_file) if blacklist_primers_file else set()
    gene_counts = {}
    for ctf in ctf_list:
        ctf_gene_set = set()
        for entry in ctf.primer_pairs:
            if entry.gsp1_name in blacklisted_primers:
                continue
            gene_name = entry.gsp1_name.split("_")[0]
            if gene_name not in ctf_gene_set:
                ctf_gene_set.add(gene_name)
                if gene_name not in gene_counts:
                    gene_counts[gene_name] = 0
                gene_counts[gene_name] += 1

    if output_file:
        with open(output_file, "w") as sw:
            for gene_name in gene_counts:
                sw.write(f"{gene_name}\t{gene_counts[gene_name]}\n")
    else:
        for gene_name in gene_counts:
            print(f"{gene_name}\t{gene_counts[gene_name]}")
