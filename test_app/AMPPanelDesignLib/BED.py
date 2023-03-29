from typing import Optional, List


class BED:
    class Entry:
        def __init__(self, chrom: str, chrom_start: int, chrom_end: int, name: str, score: str, strand: str,
                     thick_start: int, thick_end: int) -> None:
            self.chrom: str = chrom
            self.chrom_start: int = chrom_start
            self.chrom_end: int = chrom_end
            self.name: str = name
            self.score: str = score
            self.strand: str = strand
            self.thick_start: int = thick_start
            self.thick_end: int = thick_end

    def __init__(self, file_path: Optional[str], header: List[str], entries: List['BED.Entry']) -> None:
        self.file_path: Optional[str] = file_path
        self.header: List[str] = header
        self.entries: List[BED.Entry] = entries


def load_bed(bed_file: str):
    with open(bed_file, 'r') as sr:
        header = []
        entries = []
        for line in sr:
            if line.startswith("#") or line.startswith("browser") or line.startswith("track"):
                header.append(line)
            else:
                line = line.split("\t")
                entry = BED.Entry(chrom=line[0], chrom_start=int(line[1]), chrom_end=int(line[2]), name=line[3],
                                  score=line[4], strand=line[5], thick_start=int(line[6]), thick_end=int(line[7]))
                entries.append(entry)

        return BED(bed_file, header, entries)
