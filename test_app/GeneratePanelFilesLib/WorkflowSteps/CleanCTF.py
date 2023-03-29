import os
from decimal import Decimal
from typing import Dict, Tuple, Optional, List

from AMPPanelDesignLib.CTF import CTF, PrimerPair, Primer
from GeneratePanelFilesLib.Logger import Logger
from configs.ConfigurationFiles import ConfigurationFiles


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


def _load_ctf_alternate_mappings() -> Dict[Tuple[str, str], Dict[Tuple[str, str], PrimerPair]]:
    ctf_alternate_mappings_file = ConfigurationFiles.ctf_alternate_mappings_file
    ctf_alternate_mappings: Dict[Tuple[str, str], Dict[Tuple[str, str], PrimerPair]] = {}
    current_alternate_mapping_search_term: Optional[Tuple[str, str]] = None
    current_alternate_mapping_list: Optional[Dict[Tuple[str, str], PrimerPair]] = None
    with open(ctf_alternate_mappings_file, 'r') as file_reader:
        line_num = 0
        for line in file_reader:
            line_num += 1
            if line.startswith("#") or line.isspace() or not line:
                continue
            if line.startswith(">"):
                if current_alternate_mapping_search_term and current_alternate_mapping_list:
                    ctf_alternate_mappings[current_alternate_mapping_search_term] = current_alternate_mapping_list
                current_alternate_mapping_search_term = None
                current_alternate_mapping_list = {}
            else:
                if current_alternate_mapping_search_term is None:
                    line = line.rstrip().split("\t")
                    current_alternate_mapping_search_term = (line[12], line[18])
                else:
                    line = line.rstrip().split("\t")
                    gsp1_tail = line[15].casefold()
                    if gsp1_tail == "true":
                        gsp1_tail = True
                    elif gsp1_tail == "false":
                        gsp1_tail = False
                    else:
                        gsp1_tail = None
                    cds_only = line[21].casefold()
                    if cds_only == "true":
                        cds_only = True
                    elif cds_only == "false":
                        cds_only = False
                    else:
                        cds_only = None
                    new_primer_pair = PrimerPair(gene_name=line[0],
                                                 ncbi_reference_sequence=line[1],
                                                 target_exon=line[2],
                                                 target_chromosome=line[3],
                                                 target_start=line[4],
                                                 target_stop=line[5],
                                                 target_strand=line[6],
                                                 target_name=line[7],
                                                 assay_type=line[8],
                                                 direction=line[9],
                                                 gsp1=Primer(start=int(line[10]),
                                                             stop=int(line[11]),
                                                             name=line[12],
                                                             sequence=line[13],
                                                             boost_level=Decimal(line[14])),
                                                 gsp1_tail=gsp1_tail,
                                                 gsp2=Primer(start=int(line[16]),
                                                             stop=int(line[17]),
                                                             name=line[18],
                                                             sequence=line[19],
                                                             boost_level=Decimal(line[20])),
                                                 cds_only=cds_only,
                                                 primer_pair_functions=line[22],
                                                 snp_id_locations=line[23],
                                                 primer_pair_notes=line[24])
                    current_alternate_mapping_list[(new_primer_pair.gsp1_name, new_primer_pair.gsp2_name)] = new_primer_pair
        if current_alternate_mapping_search_term not in ctf_alternate_mappings:
            ctf_alternate_mappings[current_alternate_mapping_search_term] = current_alternate_mapping_list
        return ctf_alternate_mappings


aliased_gene_names_lookup = _load_aliased_gene_names()
alternate_ctf_mappings = _load_ctf_alternate_mappings()


def clean_ctf(ctf: CTF) -> CTF:
    cleaned_primer_pairs: List[PrimerPair] = []
    alternate_mappings: Dict[Tuple[str, str], PrimerPair] = {}

    for primer_pair in ctf.primer_pairs:
        gene_name = primer_pair.gene_name
        gsp1_name = primer_pair.gsp1_name
        gsp2_name = primer_pair.gsp2_name
        if gene_name in aliased_gene_names_lookup:
            gene_alias = aliased_gene_names_lookup[gene_name]
            gsp1_name = gsp1_name.replace(gene_name, gene_alias, 1)
            gsp2_name = gsp2_name.replace(gene_name, gene_alias, 1)
            gene_name = gene_alias
        new_primer_pair = PrimerPair(gene_name=gene_name,
                                     ncbi_reference_sequence=primer_pair.ncbi_reference_sequence,
                                     target_exon=primer_pair.target_exon,
                                     target_chromosome=primer_pair.target_chromosome,
                                     target_start=primer_pair.target_start,
                                     target_stop=primer_pair.target_stop,
                                     target_strand=primer_pair.target_strand,
                                     target_name=primer_pair.target_name,
                                     assay_type=primer_pair.assay_type,
                                     direction=primer_pair.direction,
                                     gsp1=Primer(start=primer_pair.gsp1.start,
                                                 stop=primer_pair.gsp1.stop,
                                                 name=gsp1_name,
                                                 sequence=primer_pair.gsp1.sequence,
                                                 boost_level=primer_pair.gsp1.boost_level),
                                     gsp1_tail=primer_pair.gsp1_tail,
                                     gsp2=Primer(start=primer_pair.gsp2.start,
                                                 stop=primer_pair.gsp2.stop,
                                                 name=gsp2_name,
                                                 sequence=primer_pair.gsp2.sequence,
                                                 boost_level=primer_pair.gsp2.boost_level),
                                     cds_only=primer_pair.cds_only,
                                     primer_pair_functions=primer_pair.primer_pair_functions,
                                     snp_id_locations=primer_pair.snp_id_locations,
                                     primer_pair_notes=primer_pair.primer_pair_notes)
        new_primer_pair_key = (new_primer_pair.gsp1_name, new_primer_pair.gsp2_name)
        if new_primer_pair_key in alternate_ctf_mappings:
            alternate_mappings.update(alternate_ctf_mappings[new_primer_pair_key])
        cleaned_primer_pairs.append(new_primer_pair)

    for primer_pair in cleaned_primer_pairs:
        primer_pair_key = (primer_pair.gsp1_name, primer_pair.gsp2_name)
        if primer_pair_key in alternate_mappings:
            alternate_mappings.pop(primer_pair_key)

    for alternate_mapping_primer_pair in alternate_mappings.values():
        cleaned_primer_pairs.append(alternate_mapping_primer_pair)

    return CTF(design_id=ctf.id, file_path=None, header=ctf.header.items, primer_pairs=cleaned_primer_pairs)


def clean_ctf_step(logger: Logger, raw_ctf: CTF, output_directory: str) -> CTF:
    logger.message("Cleaning CTF file...")
    if raw_ctf is None:
        logger.warning("No CTF file provided, skipping CTF cleaning.")
    else:
            cleaned_ctf = clean_ctf(ctf=raw_ctf)
            logger.message("CTF file successfully cleaned.")
            file_name, extension = os.path.splitext(os.path.basename(raw_ctf.file_path))
            cleaned_ctf.file_path = os.path.join(output_directory, f"{file_name}.cleaned{extension}")
            logger.message(f"Writing cleaned CTF to {cleaned_ctf.file_path}")
            cleaned_ctf.write(cleaned_ctf.file_path)
            return cleaned_ctf
