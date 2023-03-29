import os.path
from decimal import Decimal
from glob import glob
from typing import List, Dict, Optional, Set

from AMPPanelDesignLib.Enums import MoleculeType


class Primer:
    def __init__(self, start: int, stop: int, name: str, sequence: str, boost_level: Decimal) -> None:
        self.start: int = start
        self.stop: int = stop
        self.name: str = name
        self.sequence: str = sequence
        self.boost_level: Decimal = boost_level

    def __eq__(self, other: 'Primer') -> bool:
        return self.start == other.start \
               and self.stop == other.stop \
               and self.name == other.name \
               and self.sequence == other.sequence \
               and self.boost_level == other.boost_level

    def __hash__(self) -> int:
        return hash((self.start, self.stop, self.name, self.sequence, self.boost_level))


class PrimerPair:
    columns = ["gene_name", "ncbi_reference_sequence", "target_exon", "target_chromosome", "target_start",
               "target_stop", "target_strand", "target_name", "assay_type", "direction", "gsp1_start",
               "gsp1_stop", "gsp1_name", "gsp1_sequence", "gsp1_boost_level", "gsp1_tail", "gsp2_start", "gsp2_stop",
               "gsp2_name", "gsp2_sequence", "gsp2_boost_level", "cds_only", "primer_pair_functions",
               "snp_id_locations", "primer_pair_notes"]

    def __init__(self, gene_name: str, ncbi_reference_sequence: str, target_exon: str, target_chromosome: str,
                 target_start: str, target_stop: str, target_strand: str, target_name: str, assay_type: str,
                 direction: str, gsp1: Primer, gsp1_tail: bool, gsp2: Primer, cds_only: bool,
                 primer_pair_functions: str, snp_id_locations: str, primer_pair_notes: str) -> None:
        self.gene_name: str = gene_name
        self.ncbi_reference_sequence: str = ncbi_reference_sequence
        self.target_exon: str = target_exon
        self.target_chromosome: str = target_chromosome
        self.target_start: str = target_start
        self.target_stop: str = target_stop
        self.target_strand: str = target_strand
        self.target_name: str = target_name
        self.assay_type: str = assay_type
        self.direction: str = direction
        self.gsp1: Primer = gsp1
        self.gsp1_tail: bool = gsp1_tail
        self.gsp2: Primer = gsp2
        self.cds_only: bool = cds_only
        self.primer_pair_functions: str = primer_pair_functions
        self.snp_id_locations: str = snp_id_locations
        self.primer_pair_notes: str = primer_pair_notes

    @property
    def gsp1_start(self) -> int:
        return self.gsp1.start

    @property
    def gsp1_stop(self) -> int:
        return self.gsp1.stop

    @property
    def gsp1_name(self) -> str:
        return self.gsp1.name

    @property
    def gsp1_sequence(self) -> str:
        return self.gsp1.sequence

    @property
    def gsp1_boost_level(self) -> Decimal:
        return self.gsp1.boost_level

    @property
    def gsp2_start(self) -> int:
        return self.gsp2.start

    @property
    def gsp2_stop(self) -> int:
        return self.gsp2.stop

    @property
    def gsp2_name(self) -> str:
        return self.gsp2.name

    @property
    def gsp2_sequence(self) -> str:
        return self.gsp2.sequence

    @property
    def gsp2_boost_level(self) -> Decimal:
        return self.gsp2.boost_level

    def __str__(self) -> str:
        values = []
        for col_name in PrimerPair.columns:
            value = getattr(self, col_name)
            if type(value) == bool:
                value = str(value).casefold()
            else:
                value = str(value)
            values.append(value)
        return "\t".join(values)


class CTF:
    class Header:
        def __init__(self, headers: Dict[str, str]) -> None:
            self.items: Dict[str, str] = headers

        @property
        def project_name(self) -> Optional[str]:
            return self.items.get("ProjectName", None)

        @property
        def part_number(self) -> Optional[str]:
            return self.items.get("PartNumber", None)

        @property
        def project_version(self):
            # type: () -> Optional[str]
            return self.items.get("ProjectVersion", None)

        @property
        def molecule_types(self) -> Optional[Set[MoleculeType]]:
            molecule_types = set()
            molecule_type_header = self.items.get("MoleculeType", None)
            if molecule_type_header is None:
                return molecule_types
            for molecule_type in molecule_type_header.split(","):
                molecule_type = molecule_type.strip().lower()
                if not molecule_type or molecule_type.isspace():
                    continue
                if molecule_type == "rna":
                    molecule_types.add(MoleculeType.RNA)
                elif molecule_type == "dna":
                    molecule_types.add(MoleculeType.DNA)
                elif molecule_type == "ctdna":
                    molecule_types.add(MoleculeType.CTDNA)
                else:
                    raise Exception(f"Invalid molecule type ({molecule_type}) in CTF header")
            return molecule_types

        @property
        def total_gsp1_concentration(self) -> Optional[Decimal]:
            total_gsp1_concentration = self.items.get("TotalGsp1Concentration", None)
            if not total_gsp1_concentration.strip():
                return None
            return Decimal(total_gsp1_concentration)

        @property
        def total_gsp2_concentration(self) -> Optional[Decimal]:
            total_gsp2_concentration = self.items.get("TotalGsp2Concentration", None)
            if not total_gsp2_concentration.strip():
                return None
            return Decimal(total_gsp2_concentration)

        @property
        def extra_headers(self) -> Dict[str, str]:
            excluded_keys = ["ProjectName", "PartNumber", "ProjectVersion", "MoleculeType", "TotalGsp1Concentration",
                             "TotalGsp2Concentration"]
            return dict((key, self.items[key]) for key in self.items if key not in excluded_keys)

        def __getitem__(self, item):
            return self.items[item]

    def __init__(self, design_id: str, file_path: Optional[str], header: Dict[str, str],
                 primer_pairs: List[PrimerPair]) -> None:
        self.id: str = design_id
        self.file_path: Optional[str] = file_path
        self.header: CTF.Header = CTF.Header(header)
        self.primer_pairs: List[PrimerPair] = primer_pairs
        self._deduplicated_gsp1_primers: Optional[Set[Primer]] = None
        self._deduplicated_gsp2_primers: Optional[Set[Primer]] = None
        self._primer_pair_set: Optional[Set[(Primer, Primer)]] = None

    @property
    def primer_pair_set(self) -> Set[Primer]:
        if not self._primer_pair_set:
            self._primer_pair_set = set([(primer_pair.gsp1, primer_pair.gsp2) for primer_pair in self.primer_pairs])
        return self._primer_pair_set

    @property
    def unique_gsp1_primers(self) -> Set[Primer]:
        if self._deduplicated_gsp1_primers is None:
            self._deduplicated_gsp1_primers = set()
            added_primers = {}
            for pair in self.primer_pairs:
                if pair.gsp1.name not in added_primers:
                    self._deduplicated_gsp1_primers.add(pair.gsp1)
                    added_primers[pair.gsp1.name] = pair.gsp1.boost_level
                elif pair.gsp1.boost_level != added_primers[pair.gsp1.name]:
                    raise Exception(
                        f"Invalid CTF {self.file_path or '[NO FILE PATH]'}: Primer {pair.gsp1.name} has duplicates with different "
                        f"boost levels ({added_primers[pair.gsp1.name]}, {pair.gsp1.boost_level})")
        return self._deduplicated_gsp1_primers

    @property
    def gsp1_primer_units(self) -> Decimal:
        return sum(primer.boost_level for primer in self.unique_gsp1_primers)

    @property
    def unique_gsp1_count(self) -> int:
        return len(self.unique_gsp1_primers)

    @property
    def unique_gsp2_primers(self) -> Set[Primer]:
        if self._deduplicated_gsp2_primers is None:
            self._deduplicated_gsp2_primers = set()
            added_primers = {}
            for pair in self.primer_pairs:
                if pair.gsp2.name not in added_primers:
                    self._deduplicated_gsp2_primers.add(pair.gsp2)
                    added_primers[pair.gsp2.name] = pair.gsp2.boost_level
                elif pair.gsp2.boost_level != added_primers[pair.gsp2.name]:
                    raise Exception(f"Invalid CTF {self.file_path or '[NO FILE PATH]'}: Primer {pair.gsp2.name} has"
                                    f" duplicates with different boost levels ({added_primers[pair.gsp2.name]}, "
                                    f"{pair.gsp2.boost_level})")
        return self._deduplicated_gsp2_primers

    @property
    def gsp2_primer_units(self) -> Decimal:
        return sum(primer.boost_level for primer in self.unique_gsp2_primers)

    @property
    def unique_gsp2_count(self) -> int:
        return len(self.unique_gsp2_primers)

    def issubset(self, ctf: 'CTF') -> bool:
        return self.primer_pair_set.issubset(ctf.primer_pair_set)

    def isdisjoint(self, ctf: 'CTF') -> bool:
        return self.primer_pair_set.isdisjoint(ctf.primer_pair_set)

    def write(self, file_path: str) -> None:
        output_directory = os.path.dirname(file_path)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        with open(file_path, 'w') as sw:
            sw.write(f"# ProjectName: {self.header['ProjectName'] or ''}\n")
            sw.write(f"# PartNumber: {self.header['PartNumber'] or ''}\n")
            sw.write(f"# ProjectVersion: {self.header['ProjectVersion'] or ''}\n")
            sw.write(f"# MoleculeType: {self.header['MoleculeType'] or ''}\n")
            sw.write(f"# TotalGsp1Concentration: {self.header['TotalGsp1Concentration'] or ''}\n")
            sw.write(f"# TotalGsp2Concentration: {self.header['TotalGsp2Concentration'] or ''}\n")
            for header_key in self.header.extra_headers:
                sw.write(f"# {header_key}: {self.header[header_key]}\n")
            sw.write("\t".join(PrimerPair.columns) + "\n")
            for p in self.primer_pairs:
                sw.write(str(p) + "\n")


def load_ctf(ctf_file_path: str) -> CTF:
    file_name_split = os.path.basename(ctf_file_path).split("_")
    # handle Assay Designer CTF file name formats
    if file_name_split[0].isdigit():
        design_id = file_name_split[0]
    # handle Assay Marketplace CTF file name formats
    elif file_name_split[-1].startswith("MP") and file_name_split[-1].endswith(".ctf"):
        design_id = file_name_split[-1][2:7]
    else:
        raise Exception(f"Could not determine CTF design ID from file name: {ctf_file_path}")

    with open(ctf_file_path, 'r') as sr:
        header = {}
        line = sr.readline()
        line_num = 1
        while line.startswith("#"):
            split = line.split(":", 1)
            key = split[0].replace("#", "", 1).strip()
            if len(split) > 1:
                value = split[1].strip()
            else:
                value = None
            if key in header:
                raise Exception(f"Duplicate header key ({key}) in {ctf_file_path}")
            header[key] = value
            line = sr.readline()
            line_num += 1

        column_indices = line.strip().split("\t")
        column_indices = {key: column_indices.index(key) for key in column_indices}
        primer_pairs = []
        for line in sr:
            line_num += 1
            line = line.rstrip("\n").split("\t")
            if len(line) < len(column_indices):
                for _ in range(0,len(column_indices) - len(line)):
                    line.append("")
            gsp1_start = line[column_indices["gsp1_start"]]
            gsp1_stop = line[column_indices["gsp1_stop"]]
            gsp1_name = line[column_indices["gsp1_name"]]
            gsp1_sequence = line[column_indices["gsp1_sequence"]]
            gsp1_boost_level = line[column_indices["gsp1_boost_level"]]
            gsp1_tail = line[column_indices["gsp1_tail"]].casefold()
            if gsp1_tail == "true":
                gsp1_tail = True
            elif gsp1_tail == "false":
                gsp1_tail = False
            else:
                gsp1_tail = None
            gsp2_start = line[column_indices["gsp2_start"]]
            gsp2_stop = line[column_indices["gsp2_stop"]]
            gsp2_name = line[column_indices["gsp2_name"]]
            gsp2_sequence = line[column_indices["gsp2_sequence"]]
            gsp2_boost_level = line[column_indices["gsp2_boost_level"]]
            cds_only = line[column_indices["cds_only"]].casefold()
            if cds_only == "true":
                cds_only = True
            elif cds_only == "false":
                cds_only = False
            else:
                cds_only = None
            if all(field is not None and field != "" for field in
                   [gsp1_start, gsp1_stop, gsp1_name, gsp1_sequence, gsp1_boost_level, gsp1_tail, gsp2_start, gsp2_stop,
                    gsp2_name, gsp2_sequence, gsp2_boost_level]):
                primer_pair = PrimerPair(gene_name=line[column_indices["gene_name"]],
                                         ncbi_reference_sequence=line[column_indices["ncbi_reference_sequence"]],
                                         target_exon=line[column_indices["target_exon"]],
                                         target_chromosome=line[column_indices["target_chromosome"]],
                                         target_start=line[column_indices["target_start"]],
                                         target_stop=line[column_indices["target_stop"]],
                                         target_strand=line[column_indices["target_strand"]],
                                         target_name=line[column_indices["target_name"]],
                                         assay_type=line[column_indices["assay_type"]],
                                         direction=line[column_indices["direction"]],
                                         gsp1=Primer(start=int(gsp1_start),
                                                     stop=int(gsp1_stop),
                                                     name=gsp1_name,
                                                     sequence=gsp1_sequence,
                                                     boost_level=Decimal(gsp1_boost_level)),
                                         gsp1_tail=gsp1_tail,
                                         gsp2=Primer(start=int(gsp2_start),
                                                     stop=int(gsp2_stop),
                                                     name=gsp2_name,
                                                     sequence=gsp2_sequence,
                                                     boost_level=Decimal(gsp2_boost_level)),
                                         cds_only=cds_only,
                                         primer_pair_functions=line[column_indices["primer_pair_functions"]],
                                         snp_id_locations=line[column_indices["snp_id_locations"]],
                                         primer_pair_notes=line[column_indices["primer_pair_notes"]])
                primer_pairs.append(primer_pair)

        return CTF(design_id, ctf_file_path, header, primer_pairs)


def load_all_ctfs(ctf_folder_path: str, ctf_ignore_set: Optional[Set[str]] = None) -> Dict[str, CTF]:
    designs = {}
    ctf_search_results = [ctf for walk_result in os.walk(ctf_folder_path) for ctf in
                          glob(os.path.join(walk_result[0], "*.ctf"))]
    for ctf in ctf_search_results:
        if ctf_ignore_set is not None and ctf in ctf_ignore_set:
            continue
        ctf = load_ctf(ctf)
        if ctf.id in designs:
            raise Exception(f"Duplicate CTF design ID {ctf.id} found in {ctf_folder_path}")
        designs[ctf.id] = ctf
    return designs
