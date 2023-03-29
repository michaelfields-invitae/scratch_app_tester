import os

from glob import glob

from typing import List, Optional, Set, Dict


class GTF:
    class Entry:
        class Attribute:
            def __init__(self, attributes: Dict[str, str]) -> None:
                self.items: Dict[str, str] = attributes

            @property
            def name(self) -> str:
                return self.items["name"]

            @property
            def gene_id(self) -> str:
                return self.items["gene_id"]

            @property
            def exon_number(self) -> str:
                return self.items["exon_number"]

            @property
            def transcript_id(self) -> str:
                return self.items["transcript_id"]

            @property
            def function(self) -> Set[str]:
                return set(self.items["function"].split(","))

            @property
            def target_roi(self) -> Optional[str]:
                return self.items.get("target_ROI", None)

            @property
            def variant(self) -> Optional[str]:
                return self.items.get("variant", None)

            def __getitem__(self, item: str) -> str:
                return self.items[item]

            def __str__(self) -> str:
                return "; ".join(f"{key} \"{self.items[key]}\"" for key in self.items) + ";"

        def __init__(self, seqname: str, source: str, feature: str, start: int, end: int, score: str, strand: str,
                     frame: str, attributes: Dict) -> None:
            self.seqname: str = seqname
            self.source: str = source
            self.feature: str = feature
            self.start: int = start
            self.end: int = end
            self.score: str = score
            self.strand: str = strand
            self.frame: str = frame
            self.attributes: GTF.Entry.Attribute = GTF.Entry.Attribute(attributes)

        def __str__(self) -> str:
            return "\t".join([self.seqname, self.source, self.feature, str(self.start), str(self.end), self.score,
                              self.strand, self.frame, str(self.attributes)])

    def __init__(self, entries: List['GTF.Entry'], design_id: Optional[str], file_path: Optional[str]) -> None:
        self.entries = entries  # type: List[GTF.Entry]
        self.id = design_id  # type: Optional[str]
        self.file_path = file_path  # type: Optional[str]

    def write(self, file_path: str) -> None:
        output_directory = os.path.dirname(file_path)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        with open(file_path, "w") as sw:
            for entry in self.entries:
                sw.write(str(entry) + "\n")


def load_gtf(gtf_file_path: str) -> GTF:
    design_id = os.path.basename(gtf_file_path).split("_")[-1].split("-")[0]
    with open(gtf_file_path, 'r') as sr:
        line_count = 0
        entries = []
        for line in sr:
            line_count += 1
            if line.startswith("#"):
                continue
            line = line.strip().split("#", 1)[0].split("\t")
            if len(line) != 9:
                raise Exception(f"Invalid line {line_count} in {gtf_file_path} with {len(line)} fields (expecting 9).")
            attributes = {}
            for attr in line[8].rstrip(";").split(";"):
                attr = attr.strip().split(" ", 1)
                attr_key = attr[0].strip()
                attr_value = attr[1].strip('"')
                if attr_key in attributes:
                    raise Exception(f"Duplicate attribute {attr_key} found on line {line_count} in {gtf_file_path}.")
                attributes[attr_key] = attr_value

            entry = GTF.Entry(seqname=line[0], source=line[1], feature=line[2], start=int(line[3]), end=int(line[4]),
                              score=line[5], strand=line[6], frame=line[7], attributes=attributes)
            entries.append(entry)

        return GTF(entries, design_id, gtf_file_path)


def load_all_gtfs(gtf_folder_path: str) -> Dict[str, GTF]:
    designs = {}
    gtf_search_results = [gtf for walk_result in os.walk(gtf_folder_path) for gtf in
                          glob(os.path.join(walk_result[0], "*.gtf"))]
    for gtf in gtf_search_results:
        gtf = load_gtf(gtf)
        if gtf.id in designs:
            raise Exception(f"Duplicate GTF design ID {gtf.id} found in {gtf_folder_path}")
        designs[gtf.id] = gtf
    return designs
