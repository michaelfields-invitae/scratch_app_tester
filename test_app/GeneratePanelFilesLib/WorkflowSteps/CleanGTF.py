import os
from typing import Optional, List, Dict, Set

from AMPPanelDesignLib.BED import BED
from AMPPanelDesignLib.Enums import WorkflowType, DiseaseType
from AMPPanelDesignLib.GTF import GTF
from AMPPanelDesignLib.PanelInfo import PanelInfo
from GeneratePanelFilesLib.Logger import Logger
from configs.ConfigurationFiles import ConfigurationFiles


class GenomicInterval:
    def __init__(self, chrom: str, start: int, end: int) -> None:
        self.chrom: str = chrom
        self.start: int = start
        self.end: int = end

    def intersects_with(self, interval: 'GenomicInterval') -> bool:
        return self.chrom == interval.chrom and self.start <= interval.start and interval.end <= self.end

    def merge(self, interval: 'GenomicInterval') -> 'GenomicInterval':
        if not self.intersects_with(interval):
            raise Exception("Ranges cannot be merged because they do not intersect: "
                            f"({self.chrom}, {self.start}, {self.end}), ({self.chrom}, {self.start}, {self.end})")
        return GenomicInterval(self.chrom, min(self.start, interval.start), max(self.end, interval.end))

    def pad(self, padding_size):
        # type: (int) -> GenomicInterval
        return GenomicInterval(self.chrom, self.start - padding_size, self.end + padding_size)

    def __str__(self):
        # type: () -> str
        return f"{self.chrom}:{self.start}-{self.end}"


def _get_bed_targets(bed: BED) -> Dict[str, Dict[int, GenomicInterval]]:
    merged_bed_intervals: Dict[str, Dict[int, GenomicInterval]] = {}

    temp: Dict[str, List[GenomicInterval]] = {}
    for entry in bed.entries:
        if entry.chrom not in temp:
            temp[entry.chrom] = []
        temp[entry.chrom].append(GenomicInterval(entry.chrom, entry.chrom_start, entry.chrom_end))

    for chromosome in temp:
        interval_list = temp[chromosome]
        interval_list.sort(key=lambda genomic_interval: genomic_interval.start)
        merged = [interval_list[0]]
        for interval in interval_list:
            if merged[-1].intersects_with(interval):
                merged[-1] = merged[-1].merge(interval)
            else:
                merged.append(interval)
        merged_bed_intervals[chromosome] = {}
        for merged_interval in merged:
            revised_merged_interval = GenomicInterval(merged_interval.chrom, merged_interval.start + 1,
                                                      merged_interval.end)
            for i in range(merged_interval.start, merged_interval.end + 1):
                merged_bed_intervals[chromosome][i] = revised_merged_interval

    return merged_bed_intervals


def _load_special_function_flags() -> Dict[str, Set[str]]:
    special_function_flags_file = ConfigurationFiles.special_gtf_function_flags_file
    special_function_flags = {}
    column_indices = None
    with open(special_function_flags_file, 'r') as file_reader:
        for line in file_reader:
            if line.startswith("#") or line.isspace() or not line:
                continue
            line = line.strip().split("\t")
            if column_indices is None:
                column_indices = {key.lower(): line.index(key) for key in line}
            else:
                primer_name = line[column_indices["gsp2 primer name"]]
                flags = set(line[column_indices["special function flags"]].split(","))
                special_function_flags[primer_name] = flags
    return special_function_flags


def _load_special_target_roi() -> Dict[str, str]:
    special_target_roi_file = ConfigurationFiles.special_gtf_target_roi_file
    special_target_rois = {}
    column_indices = None
    with open(special_target_roi_file, 'r') as file_reader:
        for line in file_reader:
            if line.startswith("#") or line.isspace() or not line:
                continue
            line = line.strip().split("\t")
            if column_indices is None:
                column_indices = {key.lower(): line.index(key) for key in line}
            else:
                primer_name = line[column_indices["gsp2 primer name"]]
                target_roi = line[column_indices["special target roi"]]
                special_target_rois[primer_name] = target_roi
    return special_target_rois


def _load_aliased_gene_names() -> Dict[str, str]:
    aliased_gene_names_file = ConfigurationFiles.aliased_gene_names_file
    aliased_gene_names = {}
    column_indices = None
    with open(aliased_gene_names_file, 'r') as file_reader:
        for line in file_reader:
            if line.startswith("#") or line.isspace() or not line:
                continue
            line = line.strip().split("\t")
            if column_indices is None:
                column_indices = {key.lower(): line.index(key) for key in line}
            else:
                alias_gene_name = line[column_indices["gene name"]]
                replacement_gene_name = line[column_indices["replacement gene name"]]
                aliased_gene_names[alias_gene_name] = replacement_gene_name
    return aliased_gene_names


def _load_gtf_alternate_mappings() -> Dict[str, Dict[str, GTF.Entry]]:
    gtf_alternate_mappings_file = ConfigurationFiles.gtf_alternate_mappings_file
    gtf_alternate_mappings: Dict[str, Dict[str, GTF.Entry]] = {}
    current_alternate_mapping_search_term: Optional[str] = None
    current_alternate_mapping_list: Optional[Dict[str, GTF.Entry]] = None
    with open(gtf_alternate_mappings_file, 'r') as file_reader:
        line_count = 0
        for line in file_reader:
            line_count += 1
            if line.startswith("#") or line.isspace() or not line:
                continue
            if line.startswith(">"):
                if current_alternate_mapping_search_term and current_alternate_mapping_list:
                    gtf_alternate_mappings[current_alternate_mapping_search_term] = current_alternate_mapping_list
                current_alternate_mapping_search_term = None
                current_alternate_mapping_list = {}
            else:
                if current_alternate_mapping_search_term is None:
                    line = line.strip().split("\t")
                    attributes = {}
                    for attr in line[8].rstrip(";").split(";"):
                        attr = attr.strip().split(" ", 1)
                        attr_key = attr[0].strip()
                        attr_value = attr[1].strip('"')
                        if attr_key in attributes:
                            raise Exception(f"Duplicate attribute {attr_key} found on line {line_count} in "
                                            f"{gtf_alternate_mappings_file}.")
                        attributes[attr_key] = attr_value
                    current_alternate_mapping_search_term = attributes["name"]
                else:
                    line = line.strip().split("\t")
                    attributes = {}
                    for attr in line[8].rstrip(";").split(";"):
                        attr = attr.strip().split(" ", 1)
                        attr_key = attr[0].strip()
                        attr_value = attr[1].strip('"')
                        if attr_key in attributes:
                            raise Exception(f"Duplicate attribute {attr_key} found on line {line_count} in "
                                            f"{gtf_alternate_mappings_file}.")
                        attributes[attr_key] = attr_value
                    new_gtf_entry = GTF.Entry(seqname=line[0], source=line[1], feature=line[2], start=int(line[3]),
                                              end=int(line[4]), score=line[5], strand=line[6], frame=line[7],
                                              attributes=attributes)
                    current_alternate_mapping_list[attributes["name"]] = new_gtf_entry
        if current_alternate_mapping_search_term not in gtf_alternate_mappings:
            gtf_alternate_mappings[current_alternate_mapping_search_term] = current_alternate_mapping_list
        return gtf_alternate_mappings


special_function_flags_lookup = _load_special_function_flags()
special_target_roi_lookup = _load_special_target_roi()
aliased_gene_names_lookup = _load_aliased_gene_names()
alternate_gtf_mappings = _load_gtf_alternate_mappings()


def clean_gtf(gtf: GTF, base_gtfs: Optional[Set[GTF]], workflow: WorkflowType, disease: DiseaseType, bed: BED,
              max_distance: int, gtf_target_roi_buffer: Optional[int], analysis_version: str) -> GTF:
    cleaned_entries: Dict[str, GTF.Entry] = {}
    alternate_mappings: Dict[str, GTF.Entry] = {}

    is_variantplex = workflow in [WorkflowType.VARIANTPLEXSTANDARD, WorkflowType.VARIANTPLEXHS,
                                  WorkflowType.VARIANTPLEXHGC,
                                  WorkflowType.VARIANTPLEXHGC2]
    added_targets = set()
    if base_gtfs is not None:
        for base_gtf in base_gtfs:
            for entry in base_gtf.entries:
                cleaned_entries[entry.attributes["name"]] = entry
                added_targets.add(entry.attributes.name)

    bed_targets = _get_bed_targets(bed)

    for entry in gtf.entries:
        if entry.attributes.name in added_targets:
            continue
        new_attributes = {}
        name = entry.attributes.items["name"]
        gene_id = entry.attributes.items.get("gene_id", "")
        if gene_id in aliased_gene_names_lookup:
            name = name.replace(gene_id, aliased_gene_names_lookup[gene_id], 1)
            gene_id = aliased_gene_names_lookup[gene_id]
        new_attributes["name"] = name
        new_attributes["gene_id"] = gene_id
        exon_number = entry.attributes.items.get("exon_number", "")
        new_attributes["exon_number"] = exon_number
        transcript_id = entry.attributes.items.get("transcript_id", "")
        new_attributes["transcript_id"] = transcript_id

        if entry.attributes.name in special_function_flags_lookup:
            function_flags = ",".join(
                entry.attributes.function.union(special_function_flags_lookup[entry.attributes.name]))
        else:
            function_flags = entry.attributes.items["function"]

        # Ignore CNV_NO_DISPLAY if analysis version is 6.x
        if int(analysis_version.split(".")[0]) < 7:
            function_flags = function_flags.split(",")
            if "CNV_NO_DISPLAY" in function_flags:
                function_flags.remove("CNV_NO_DISPLAY")
            function_flags = ",".join(function_flags)

        new_attributes["function"] = function_flags

        if "variant" in entry.attributes.items:
            new_attributes["variant"] = entry.attributes.items["variant"]
        if "target_ROI" in entry.attributes.items:
            new_attributes = entry.attributes.items["target_ROI"]

        has_snv_function = "SNV" in new_attributes["function"]
        if "target_ROI" not in new_attributes and is_variantplex and has_snv_function:
            if gtf_target_roi_buffer is not None:
                padding = gtf_target_roi_buffer
            elif disease in [DiseaseType.GERMLINE, DiseaseType.SOLIDTUMOR, DiseaseType.SARCOMA]:
                padding = 10
            elif disease in [DiseaseType.BLOODCANCERS]:
                padding = 20
            else:
                raise Exception(f"Unrecognized disease type {disease}")

            if entry.attributes.name in special_target_roi_lookup:
                new_attributes["target_ROI"] = special_target_roi_lookup[entry.attributes.name]
            else:
                target_roi_found = False
                for distance in range(0, max_distance + 1):
                    if entry.strand == "+":
                        coordinate = distance + entry.end
                    elif entry.strand == "-":
                        coordinate = entry.start - distance
                    else:
                        raise Exception(f"Unsupported strand type \"{entry.strand}\" detected in coverage BED file")
                    if entry.seqname not in bed_targets:
                        raise Exception(
                            f"GTF seqname ({entry.seqname}) not found in BED file {bed.file_path or ''}. Try increasing the Max Target ROI Distance.")
                    if coordinate in bed_targets[entry.seqname]:
                        new_attributes["target_ROI"] = str(
                            bed_targets[entry.seqname][coordinate].pad(padding_size=padding))
                        target_roi_found = True
                        break

                if not target_roi_found:
                    raise Exception(
                        f"Could not find target_ROI for target ({entry.attributes.name}) in GTF {gtf.file_path or ''}")

        new_entry = GTF.Entry(seqname=entry.seqname, source=entry.source, feature=entry.feature, start=entry.start,
                              end=entry.end, score=entry.score, strand=entry.strand, frame=entry.frame,
                              attributes=new_attributes)
        if new_entry.attributes["name"] in cleaned_entries:
            continue
        new_entry_key = new_entry.attributes["name"]
        if new_entry_key in alternate_gtf_mappings:
            alternate_mappings.update(alternate_gtf_mappings[new_entry_key])
        cleaned_entries[new_entry.attributes["name"]] = new_entry

    for entry in cleaned_entries.values():
        entry_key = entry.attributes["name"]
        if entry_key in alternate_mappings:
            alternate_mappings.pop(entry_key)

    for alternate_mapping_entry in alternate_mappings.values():
        if alternate_mapping_entry.attributes["name"] not in cleaned_entries:
            cleaned_entries[alternate_mapping_entry.attributes["name"]] = alternate_mapping_entry

    return GTF(entries=list(cleaned_entries.values()), design_id=gtf.id, file_path=None)


def clean_gtf_step(logger: Logger, panel_info: PanelInfo, raw_gtf: GTF, bed: BED, catalog_gtfs: Set[GTF], output_directory: str) -> GTF:
    logger.message("Cleaning GTF file...")
    if panel_info is None:
        logger.warning("No Panel Info config file provided, skipping GTF cleaning.")
    elif raw_gtf is None:
        logger.warning("No GTF file provided, skipping GTF cleaning.")
    else:
        if panel_info.workflow in [WorkflowType.VARIANTPLEXSTANDARD, WorkflowType.VARIANTPLEXHS,
                                   WorkflowType.VARIANTPLEXHGC, WorkflowType.VARIANTPLEXHGC2] \
                and any("SNV" in entry.attributes.function for entry in raw_gtf.entries) and bed is None:
            logger.warning("No target coverage file provided for calculating target_ROI, skipping GTF cleaning.")
        else:
            cleaned_gtf = clean_gtf(gtf=raw_gtf, base_gtfs=catalog_gtfs, workflow=panel_info.workflow,
                                    disease=panel_info.disease, bed=bed,
                                    max_distance=panel_info.max_target_roi_distance,
                                    gtf_target_roi_buffer=panel_info.gtf_roi_target_buffer,
                                    analysis_version=panel_info.analysis_version)
            logger.message("GTF file successfully cleaned.")
            file_name, extension = os.path.splitext(os.path.basename(raw_gtf.file_path))
            cleaned_gtf.file_path = os.path.join(output_directory, f"{file_name}.cleaned{extension}")
            logger.message(f"Writing cleaned GTF to {cleaned_gtf.file_path}")
            cleaned_gtf.write(cleaned_gtf.file_path)
            return cleaned_gtf
