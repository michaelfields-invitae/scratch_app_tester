import os


class ConfigurationFiles:
    aliased_gene_names_file: str = os.path.join(os.path.dirname(__file__), "aliased_gene_names.txt")
    catalog_panels_file: str = os.path.join(os.path.dirname(__file__), "catalog_panels.txt")
    ctf_alternate_mappings_file: str = os.path.join(os.path.dirname(__file__), "ctf_alternate_mappings.txt")
    gtf_alternate_mappings_file: str = os.path.join(os.path.dirname(__file__), "gtf_alternate_mappings.txt")
    special_gtf_function_flags_file: str = os.path.join(os.path.dirname(__file__), "special_gtf_function_flags.txt")
    special_gtf_target_roi_file: str = os.path.join(os.path.dirname(__file__), "special_gtf_target_roi.txt")
