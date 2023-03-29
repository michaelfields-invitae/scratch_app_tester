import copy
import os
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Set, FrozenSet

from AMPPanelDesignLib.CTF import CTF, PrimerPair
from AMPPanelDesignLib.Enums import DiseaseType
from AMPPanelDesignLib.Enums import WorkflowType, MoleculeType, GSPType
from AMPPanelDesignLib.InventoryTracking import InventoryTracking
from AMPPanelDesignLib.PanelInfo import PanelInfo
from AMPPanelDesignLib.PanelInfo import RawMaterialInfo, catalog_panel_lookup, CatalogPanelPart, CatalogPanelSubPart
from GeneratePanelFilesLib.Logger import Logger


# The purpose of this graph is to help find the set of CTFs with the greatest combined GSP1/2 primer count while resolving
# all conflicts/incompatibilities between CTF files so that the final set does not contain any duplicate GSP1/2 primers.
class CTFCompatibilityGraph:
    def __init__(self) -> None:
        self._graph: Dict[CTF, Set[CTF]] = {}

    # Each node in this graph is a CTF. Edges between nodes represent compatibility between two CTFs. Two CTFs are
    # considered compatible if their unique GSP1/2 primer sets are completely disjoint, meaning they do not share any
    # GSP1/2 primers. The graph is represented by an adjacency list that is implemented using a Dict[CTF, Set[CTF]].
    # Upon adding a new CTF to this graph, the new CTF is compared against all previously added CTFs to
    # check whether or not they are compatible. If the CTFs are compatible, then both CTFs are added to each other's
    # edge lists.
    def add(self, new_ctf: CTF) -> None:
        if new_ctf in self._graph:
            raise Exception(f"Cannot add same CTF {new_ctf.file_path or '[NO FILE PATH]'} twice.")

        compatible_ctfs = set()
        for ctf in self._graph:
            if new_ctf.unique_gsp1_primers.isdisjoint(ctf.unique_gsp1_primers) \
                    and new_ctf.unique_gsp2_primers.isdisjoint(ctf.unique_gsp2_primers):
                compatible_ctfs.add(ctf)
                self._graph[ctf].add(new_ctf)
        self._graph[new_ctf] = compatible_ctfs

    def get_largest_ctf_set(self) -> FrozenSet[CTF]:
        solved_subgraphs = {}
        solution = self._get_largest_ctf_set(self._graph, solved_subgraphs)
        return solution

    # This recursive protected method contains the main algorithm for solving the problem of finding the set of
    # non-overlapping CTFs from a graph with the greatest number of unique GSP1/2 primers. This is a top-down dynamic
    # programming algorithm that seeks to break down the graph into many sub-graphs. The optimal solution to this
    # graph is the union of the optimal solutions of its sub-graphs.
    # 1. Given a graph, iterate through each of its nodes to find all candidate solutions.
    # 1a. If the iterated node is adjacent to all other nodes in the graph, then it is guaranteed to be included
    #     in all solutions for this graph
    # 1b. If the iterated node has no adjacent nodes at all, then it is by itself a candidate solution for this graph
    # 2. Assuming neither 1a and 1b are true, build a sub-graph that includes the iterated node and all of its adjacent
    #    nodes. Then try to find the optimal solution for this sub-graph by recursively starting from step 1 again using
    #    the sub-graph. This will continue breaking down the sub-graph into smaller and smaller sub-graphs until all
    #    nodes in a sub-graph meet the conditions for either 1a or 1b.
    # 3. Once all nodes in the graph have been iterated over, we will have a list of candidate solutions comprised of
    #    the optimal solutions for each of the sub-graphs. Sort the list to find the solution with the greatest number
    #    of unique GSP1/2 primers. In case of a tie, choose the solution with the fewest number of CTF files.
    # 3b. It is possible that the same sub-graph will be examined multiple times. Rather than attempting to
    #     recalculate the solution for the sub-graph again each time, we will save the solution and reuse it everytime
    #     we encounter the same sub-graph.
    def _get_largest_ctf_set(self, graph: Dict[CTF, Set[CTF]], solved_subgraphs: Dict[FrozenSet[CTF], FrozenSet[CTF]]) -> FrozenSet[CTF]:
        graph_nodes = frozenset(graph.keys())
        # If we've already solved this subgraph, don't bother solving it again and just use the saved solution
        if graph_nodes in solved_subgraphs:
            return solved_subgraphs[graph_nodes]

        base_solution: Set[CTF] = set()
        candidate_solutions: Set[FrozenSet[CTF]] = set()
        for node in graph_nodes:
            adjacent_nodes = self._graph[node].intersection(graph_nodes)
            # If this node is adjacent to all other nodes in this graph then it is guaranteed to appear in the
            # final solution for this graph, so don't bother solving its subgraph.
            if len(adjacent_nodes) == len(graph_nodes) - 1:
                base_solution.add(node)
            # If this node does not have any adjacent nodes, then it is a candidate solution all by itself.
            elif not any(adjacent_nodes):
                candidate_solutions.add(frozenset({node}))
            # If this node does have adjacent nodes but is not adjacent to all other nodes in this graph, then we need
            # to find the best solution from this subgraph.
            else:
                subgraph = {node: adjacent_nodes}
                for compatible_node in adjacent_nodes:
                    subgraph[compatible_node] = self._graph[compatible_node].intersection(adjacent_nodes)
                    subgraph[compatible_node].add(node)
                subgraph_solution = frozenset(self._get_largest_ctf_set(subgraph, solved_subgraphs))
                candidate_solutions.add(subgraph_solution)

        optimal_solution = base_solution
        if any(candidate_solutions):
            # The best candidate solution is the one with the most unique GSP primers, and the # of least CTFs in case
            # of a tie. If there are multiple solutions with identical GSP primer counts and # of CTFs, a solution will
            # be chosen arbitrarily
            def primer_count(ctf_set): return sum([len(ctf.primer_pair_set) for ctf in ctf_set])

            def ctf_count(ctf_set): return len(ctf_set)

            candidate_solutions_list = list(candidate_solutions)
            candidate_solutions_list.sort(key=lambda candidate: (-primer_count(candidate), ctf_count(candidate)))
            optimal_solution = base_solution.union(candidate_solutions_list[0])

        solved_subgraphs[graph_nodes] = frozenset(optimal_solution)
        return solved_subgraphs[graph_nodes]


def get_raw_materials(raw_ctf: CTF, workflow_type: WorkflowType, ctf_library: Dict[str, CTF],
                      spike_in_library: Dict[str, CTF]) -> (List[RawMaterialInfo], List[RawMaterialInfo], List[CTF]):
    inventoried_ctfs, spike_in_ctfs = _calculate_component_ctfs(raw_ctf, workflow_type, ctf_library, spike_in_library)

    gsp1_pool_concentration_um = raw_ctf.header.total_gsp1_concentration or Decimal(100)
    gsp2_pool_concentration_um = raw_ctf.header.total_gsp2_concentration or _calculate_gsp2_pool_concentration(raw_ctf)
    gsp1_reagent_info = _calculate_reagent_volumes(inventoried_ctfs, spike_in_ctfs, gsp1_pool_concentration_um,
                                                   GSPType.GSP1)
    gsp2_reagent_info = _calculate_reagent_volumes(inventoried_ctfs, spike_in_ctfs, gsp2_pool_concentration_um,
                                                   GSPType.GSP2)

    return gsp1_reagent_info, gsp2_reagent_info, list(spike_in_ctfs)


def _calculate_gsp2_pool_concentration(ctf: CTF) -> Decimal:
    if ctf.unique_gsp2_count < 20:
        return Decimal(10)
    elif ctf.unique_gsp2_count < 200:
        return Decimal(0.5) * Decimal(ctf.unique_gsp2_count)
    else:
        return Decimal(100)


def _calculate_component_ctfs(raw_ctf: CTF, workflow_type: WorkflowType, ctf_library: Dict[str, CTF],
                              spike_in_library: Dict[str, CTF]) -> (FrozenSet[CTF], FrozenSet[CTF]):
    candidate_ctfs = CTFCompatibilityGraph()

    if workflow_type in [WorkflowType.VARIANTPLEXSTANDARD, WorkflowType.VARIANTPLEXHGC2, WorkflowType.VARIANTPLEXHGC,
                         WorkflowType.VARIANTPLEXHS]:
        matching_molecule_type = MoleculeType.DNA
    elif workflow_type is WorkflowType.LIQUIDPLEX:
        matching_molecule_type = MoleculeType.CTDNA
    elif workflow_type is WorkflowType.FUSIONPLEX:
        matching_molecule_type = MoleculeType.RNA
    else:
        raise Exception(f"Unrecognized workflow: {workflow_type}")

    for ctf in ctf_library.values():
        if matching_molecule_type not in ctf.header.molecule_types:
            continue
        ctf_gsp1_pool_concentration = ctf.header.total_gsp1_concentration or Decimal(100)
        ctf_gsp2_pool_concentration = ctf.header.total_gsp2_concentration or Decimal(100)
        if ctf_gsp1_pool_concentration != Decimal(100) or ctf_gsp2_pool_concentration != Decimal(100):
            continue
        if ctf.issubset(raw_ctf):
            candidate_ctfs.add(ctf)

    spike_in_candidate_ctfs = set()
    if spike_in_library:
        for ctf in spike_in_library.values():
            if matching_molecule_type not in ctf.header.molecule_types:
                continue
            ctf_gsp1_pool_concentration = ctf.header.total_gsp1_concentration or Decimal(100)
            ctf_gsp2_pool_concentration = ctf.header.total_gsp2_concentration or Decimal(100)
            if ctf_gsp1_pool_concentration != Decimal(100) \
                    or ctf_gsp2_pool_concentration != Decimal(100):
                continue
            if ctf.issubset(raw_ctf):
                candidate_ctfs.add(ctf)
                spike_in_candidate_ctfs.add(ctf)

    solution_ctf_set = candidate_ctfs.get_largest_ctf_set()
    spike_in_ctfs = _calculate_spike_in_ctfs(solution_ctf_set, raw_ctf)

    inventoried_ctfs = set()
    for ctf in solution_ctf_set:
        if ctf in spike_in_candidate_ctfs:
            spike_in_ctfs.add(ctf)
        else:
            inventoried_ctfs.add(ctf)

    return frozenset(inventoried_ctfs), frozenset(spike_in_ctfs)


def _calculate_spike_in_ctfs(inventoried_ctf_set: FrozenSet[CTF], raw_ctf: CTF) -> Set[CTF]:
    inventoried_primer_pairs = set(
        [(primer_pair.gsp1, primer_pair.gsp2) for ctf in inventoried_ctf_set for primer_pair in ctf.primer_pairs])
    spike_in_ctfs = set()  # type: Set[CTF]

    if inventoried_primer_pairs != raw_ctf.primer_pair_set:
        # Find all the primer pairs from the raw CTF that are not found in the inventoried CTFs of the solution
        # and group them by gene name. We want to try to keep all the primer pairs for a given gene in the same CTF if possible
        per_gene_spike_ins = {}  # type: Dict[str, List[PrimerPair]]
        for primer_pair in raw_ctf.primer_pairs:
            if (primer_pair.gsp1, primer_pair.gsp2) not in inventoried_primer_pairs:
                gene_name = primer_pair.gsp1_name.split("_")[0]
                if gene_name not in per_gene_spike_ins:
                    per_gene_spike_ins[gene_name] = []
                per_gene_spike_ins[gene_name].append(primer_pair)

        # Clean up the per-gene primer pair lists so that there are no lists with more than the maximum allowed number
        # of primer pairs per CTF
        max_primer_pairs_per_ctf = 550
        spike_in_primer_pair_lists = []  # type: List[List[PrimerPair]]
        for per_gene_primer_pair_list in per_gene_spike_ins.values():
            for _ in range(len(per_gene_primer_pair_list) // max_primer_pairs_per_ctf):
                primer_pair_list = []  # type: List[PrimerPair]
                for _ in range(max_primer_pairs_per_ctf):
                    primer_pair_list.append(per_gene_primer_pair_list.pop())
                spike_in_primer_pair_lists.append(per_gene_primer_pair_list)
            if any(per_gene_primer_pair_list):
                spike_in_primer_pair_lists.append(per_gene_primer_pair_list)

        # Use first-fit-decreasing bin packing algorithm to group these primer pair lists in (approximately) as few CTF
        # files as possible.
        spike_in_primer_pair_lists.sort(key=lambda l: len(l), reverse=True)
        spike_in_primer_pair_bins = [[]]  # type: List[List[PrimerPair]]
        for primer_pair_list in spike_in_primer_pair_lists:
            bin_found = False
            for primer_pair_bin in spike_in_primer_pair_bins:
                if bin_found:
                    break
                free_bin_space = max_primer_pairs_per_ctf - len(primer_pair_bin)
                if free_bin_space >= len(primer_pair_list):
                    primer_pair_bin.extend(primer_pair_list)
                    bin_found = True
            if not bin_found:
                spike_in_primer_pair_bins.append(primer_pair_list)

        # Create spike-in CTF files
        ctf_count = 0
        for primer_pair_bin in spike_in_primer_pair_bins:
            ctf_count += 1
            ctf_id = f"Spike_In_{str(ctf_count)}"
            header = copy.copy(raw_ctf.header.items)
            header["ProjectName"] = f"Spike In Pool {ctf_count} {raw_ctf.header.project_name}"
            header["PartNumber"] = ""
            header["ProjectVersion"] = ""
            header["TotalGsp1Concentration"] = "100.0"
            header["TotalGsp2Concentration"] = "100.0"
            ctf = CTF(ctf_id, None, header, primer_pair_bin)
            spike_in_ctfs.add(ctf)

    return spike_in_ctfs


def _calculate_reagent_volumes(inventoried_ctfs: FrozenSet[CTF], spike_in_ctfs: FrozenSet[CTF],
                               pool_concentration_um: Decimal, gsp_type: GSPType) -> List[RawMaterialInfo]:
    def gsp_primer_units(ctf: CTF, _gsp_type: GSPType) -> Decimal:
        if _gsp_type is GSPType.GSP1:
            return ctf.gsp1_primer_units
        elif _gsp_type is GSPType.GSP2:
            return ctf.gsp2_primer_units
        else:
            raise Exception(f"Unrecognized GSP type {_gsp_type}")

    def gsp_part_number(ctf: CTF, _gsp_type: GSPType) -> str:
        if _gsp_type is GSPType.GSP1:
            suffix = "-1"
        elif _gsp_type is GSPType.GSP2:
            suffix = "-2"
        else:
            raise Exception(f"Unrecognized GSP type {_gsp_type}")

        if ctf.id.isdigit():
            return f"AD{int(ctf.id)}{suffix}"
        else:
            return f"{ctf.id}{suffix}"

    def gsp_catalog_sub_parts(catalog_panel_part: CatalogPanelPart, _gsp_type: GSPType) -> List[CatalogPanelSubPart]:
        if _gsp_type is GSPType.GSP1:
            return list(catalog_panel_part.gsp1_parts.values())
        elif _gsp_type is GSPType.GSP2:
            return list(catalog_panel_part.gsp2_parts.values())

    raw_materials: List[RawMaterialInfo] = []
    total_primer_units = Decimal(sum([gsp_primer_units(ctf, gsp_type) for ctf in inventoried_ctfs]))
    if any(spike_in_ctfs):
        total_primer_units += Decimal(sum([gsp_primer_units(ctf, gsp_type) for ctf in spike_in_ctfs]))

    for ctf in inventoried_ctfs:
        if ctf.id in catalog_panel_lookup:
            catalog_part = catalog_panel_lookup[ctf.id]
            catalog_sub_parts = gsp_catalog_sub_parts(catalog_part, gsp_type)
            if len(catalog_sub_parts) == 1:
                proportion = gsp_primer_units(ctf, gsp_type) / total_primer_units
                volume = proportion * pool_concentration_um / Decimal(100)
                raw_material = RawMaterialInfo(part_number=catalog_sub_parts[0].part_number, design_id=ctf.id,
                                               volume=volume, is_catalog_panel=True, spike_in_erp_description=None)
                raw_materials.append(raw_material)
            else:
                if sum([sub_part.boost_level_sum for sub_part in catalog_sub_parts]) != gsp_primer_units(ctf, gsp_type):
                    raise Exception(f"Sum of {gsp_type.value} boost levels in the catalog_panels.txt file for {ctf.id} does not "
                                    f"equal the value calculated from {ctf.file_path} ({gsp_primer_units(ctf, gsp_type)}).")
                for sub_part in catalog_sub_parts:
                    proportion = sub_part.boost_level_sum / total_primer_units
                    volume = proportion * pool_concentration_um / Decimal(100)
                    raw_material = RawMaterialInfo(part_number=sub_part.part_number, design_id=ctf.id, volume=volume,
                                                   is_catalog_panel=True, spike_in_erp_description=None)
                    raw_materials.append(raw_material)
        else:
            proportion = gsp_primer_units(ctf, gsp_type) / total_primer_units
            volume = proportion * pool_concentration_um / Decimal(100)
            raw_material = RawMaterialInfo(part_number=gsp_part_number(ctf, gsp_type), design_id=ctf.id, volume=volume,
                                           is_catalog_panel=False, spike_in_erp_description=None)
            raw_materials.append(raw_material)

    for ctf in spike_in_ctfs:
        proportion = gsp_primer_units(ctf, gsp_type) / total_primer_units
        volume = proportion * pool_concentration_um / Decimal(100)
        raw_material = RawMaterialInfo(part_number=gsp_part_number(ctf, gsp_type), design_id=ctf.id, volume=volume,
                                       is_catalog_panel=False,
                                       spike_in_erp_description="PLACEHOLDER_ERP_DESCRIPTION")
        raw_materials.append(raw_material)

    if gsp_type is GSPType.GSP2:
        gsp2_primer_volume = sum(raw_material.volume for raw_material in raw_materials)
        water_volume = (Decimal(1) - gsp2_primer_volume).quantize(Decimal("1e-5"))
        if water_volume != Decimal(0):
            raw_materials.append(RawMaterialInfo(part_number="DX0612", design_id=None, volume=water_volume,
                                                 is_catalog_panel=False, spike_in_erp_description=None))

    _round_raw_material_volumes(raw_materials)
    raw_materials.sort(key=lambda rm: rm.volume, reverse=True)
    return raw_materials


def _round_raw_material_volumes(raw_materials: List[RawMaterialInfo]) -> None:
    # An issue with the calculated raw material volumes is that we are limited to 5 decimals of precision
    # because the liquid handling robot is only capable of precision to hundredths of a microliter (i.e. 0.00001 mL).
    # If we simply round each of the raw material volumes to 5 decimals, the rounding errors will accumulate over
    # many raw material volumes and in many cases the sum of the volumes will no longer equal 1 mL. Instead, we'll
    # often get something very close like 0.99997 or 1.00001. This has real impacts on the manufacturing process
    # as they will build to this rounded volume but label it as 1mL. In some cases, the rounding errors will cause
    # a pure water part to be added to the GSP2 bulk intermediate build for just a few hundredths of a microliter.

    # To solve this problem, we are implementing the Largest Remainder Method for apportionment problems here.
    # To summarize, we take all the raw material volumes and round DOWN to 5 decimals. We keep a running list of the
    # raw materials and their remainders (i.e. original volume - rounded volume). This list is sorted in
    # descending order. After all the raw material volumes have been rounded down, we calculate accumulated rounding
    # error, which is the difference between 1.00000 mL and the sum of the rounded volumes. For instance, if the total
    # volume after rounding is 0.99997 mL, then the accumulated rounding error is .00003 mL. 0.00001 mL is added
    # to the volumes of the top N raw materials with the largest remainders where
    # N == (1.00000 - rounded volume)/0.00001.
    # This ensures that the total volume will always equal 1.00000 mL and that the distribution of the accumulated
    # rounding error is prioritized for the raw materials whose volumes prior to rounding were closest to
    # the next 0.00001 mL

    # There are some limitations to this approach, particularly in the case of breaking ties. For instance, if there
    # is a bulk intermediate that is equally divided between 3 raw materials (i.e. volumes of 0.33333...), one of
    # the raw materials will arbitrarily be rounded to 0.33334 while the other two remain 0.33333, even though they
    # should actually be equal volumes. This is because we are prioritizing ensuring that the total volume
    # is always 1 mL over ensuring that the relative proportions of each raw material is represented accurately
    raw_material_lookup: Dict[str, RawMaterialInfo] = {}
    volume_remainders: List[(str, Decimal)] = []
    for rm in raw_materials:
        raw_material_lookup[rm.part_number] = rm
        rounded_down_volume = rm.volume.quantize(Decimal('1e-5'), ROUND_DOWN)
        remainder = rm.volume - rounded_down_volume
        volume_remainders.append((rm.part_number, remainder))
        rm.volume = rounded_down_volume
    volume_remainders.sort(key=lambda x: x[1], reverse=True)
    rounded_down_total_volume = sum(r.volume for r in raw_materials)
    surplus_volume = Decimal(1.00000) - rounded_down_total_volume
    if surplus_volume != Decimal(0):
        surplus_count = int((surplus_volume / Decimal(0.00001)).quantize(Decimal("1")))
        for i in range(surplus_count):
            design_id = volume_remainders[i][0]
            raw_material = raw_material_lookup[design_id]
            new_volume = (raw_material.volume + Decimal(0.00001)).quantize(Decimal('1e-5'))
            raw_material.volume = new_volume


def _calculate_fill_volumes(workflow: WorkflowType, disease: DiseaseType, unique_gsp2_count: int) -> (Decimal, Decimal):
    if unique_gsp2_count < 20:
        raise Exception("Cannot calculate actual and nominal fill volumes when unique GSP2 count is less than 20")

    if workflow is WorkflowType.FUSIONPLEX:
        return Decimal("0.02000"), Decimal("16")
    elif workflow is WorkflowType.LIQUIDPLEX:
        if unique_gsp2_count < 1000:
            return Decimal("0.04000"), Decimal("32")
        elif unique_gsp2_count < 3000:
            return Decimal("0.08000"), Decimal("64")
        elif unique_gsp2_count < 8000:
            return Decimal("0.15000"), Decimal("128")
        else:
            return Decimal("0.22500"), Decimal("192")
    elif workflow in [WorkflowType.VARIANTPLEXSTANDARD, WorkflowType.VARIANTPLEXHGC,
                      WorkflowType.VARIANTPLEXHGC2, WorkflowType.VARIANTPLEXHS]:
        if disease is DiseaseType.GERMLINE:
            if unique_gsp2_count < 2000:
                return Decimal("0.02000"), Decimal("16")
            elif unique_gsp2_count < 4000:
                return Decimal("0.04000"), Decimal("32")
            else:
                return Decimal("0.08000"), Decimal("64")
        else:
            if unique_gsp2_count < 1000:
                return Decimal("0.04000"), Decimal("32")
            elif unique_gsp2_count < 3000:
                return Decimal("0.08000"), Decimal("64")
            elif unique_gsp2_count < 8000:
                return Decimal("0.15000"), Decimal("128")
            else:
                return Decimal("0.22500"), Decimal("192")
    else:
        raise Exception(f"Unsupported workflow type {workflow}")


def calculate_raw_material_volumes_step(logger: Logger, panel_info: PanelInfo, ctf: CTF, ctf_repository: Dict[str, CTF],
                                        spike_in_repository: Dict[str, CTF],
                                        output_directory: str) -> (PanelInfo, List[RawMaterialInfo],
                                                                   List[RawMaterialInfo], List[CTF]):
    logger.message("Calculating raw material volumes...")
    if panel_info is None:
        logger.warning("No Panel Info config file provided, skipping raw material volume calculation.")
        return [], [], []
    elif ctf is None:
        logger.warning("No CTF file provided, skipping raw material volume calculation.")
        return [], [], []
    elif ctf_repository is None:
        logger.warning("No CTF repository folder provided, skipping raw material volume calculation.")
        return [], [], []
    else:
        if any(panel_info.gsp1_raw_materials) or any(panel_info.gsp2_raw_materials):
            logger.warning(
                "GSP1 and/or GSP2 raw materials detected in input Panel Info config file. These volumes will be "
                "ignored and recalculated from the input CTF file. Use the --no-volume-calculation flag or do "
                "not provide an input CTF file if you wish to generate a BOM file using the volumes in the "
                "Panel Info config file.")
        gsp1_raw_materials, gsp2_raw_materials, spike_in_ctfs = get_raw_materials(raw_ctf=ctf,
                                                                                  workflow_type=panel_info.workflow,
                                                                                  ctf_library=ctf_repository,
                                                                                  spike_in_library=spike_in_repository)

        if len(gsp1_raw_materials) == 1 and len(gsp2_raw_materials) == 1 and len(spike_in_ctfs) == 1:
            logger.warning("No inventoried parts could be used, but the total number of primers is <= 550, meaning"
                           "this panel can be ordered as bulk.")
            panel_info.gsp1_raw_materials = []
            panel_info.gsp2_raw_materials = []
        else:
            panel_info.gsp1_raw_materials = gsp1_raw_materials
            panel_info.gsp2_raw_materials = gsp2_raw_materials

        fill_volumes = [panel_info.actual_fill_volume_ml_gsp1, panel_info.nominal_fill_volume_ul_gsp1,
                        panel_info.actual_fill_volume_ml_gsp2, panel_info.nominal_fill_volume_ul_gsp2]
        if all([vol is None for vol in fill_volumes]):
            logger.message("Calculating GSP1 and GSP2 bulk intermediate nominal and actual fill volumes...")
            actual_fill_volume, nominal_fill_volume = _calculate_fill_volumes(panel_info.workflow,
                                                                              panel_info.disease,
                                                                              ctf.unique_gsp2_count)
            panel_info.actual_fill_volume_ml_gsp1 = actual_fill_volume
            panel_info.actual_fill_volume_ml_gsp2 = actual_fill_volume
            panel_info.nominal_fill_volume_ul_gsp1 = nominal_fill_volume
            panel_info.nominal_fill_volume_ul_gsp2 = nominal_fill_volume
        elif not all([vol is not None for vol in fill_volumes]):
            raise Exception(
                f"Missing fill volume settings detected in {panel_info.file_path}.")

        for ctf in spike_in_ctfs:
            if not ctf.file_path:
                spike_in_ctf_path = os.path.join(output_directory, f"{panel_info.panel_id}_{ctf.id}.ctf")
                logger.message(f"Writing spike-in CTF to {spike_in_ctf_path}")
                ctf.write(spike_in_ctf_path)

        return gsp1_raw_materials, gsp2_raw_materials, spike_in_ctfs
