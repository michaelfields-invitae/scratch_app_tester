from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List


class GLILotInfo:
    def __init__(self, description: str, part_number: str, tube_code: str, volume_remaining: Decimal, lot_number: str,
                 expiration_date: date) -> None:
        self.description: str = description
        self.part_number: str = part_number
        self.tube_code: str = tube_code
        self.volume_remaining: Decimal = volume_remaining
        self.lot_number: str = lot_number
        self.expiration_date: date = expiration_date


class InventoryTracking:
    def __init__(self, parts: Dict[str, List[GLILotInfo]]) -> None:
        self._parts: Dict[str, List[GLILotInfo]] = parts

    def __getitem__(self, part_number: str) -> List[GLILotInfo]:
        return self._parts[part_number]

    def __contains__(self, part_number: str) -> bool:
        return part_number in self._parts

    def __len__(self) -> int:
        return sum(len(part_list) for part_list in self._parts.values())


def load_inventory_tracking(inventory_file_path: str) -> InventoryTracking:
    with open(inventory_file_path, 'r') as inventory_file:
        column_indices = inventory_file.readline().strip().split("\t")
        column_indices = {key: column_indices.index(key) for key in column_indices}
        parts = {}
        for line in inventory_file:
            line = line.rstrip("\n").split("\t")
            try:
                expiration_date = datetime.strptime(line[column_indices["EXP"]], "%d-%B-%y")
            except ValueError:
                try:
                    expiration_date = datetime.strptime(line[column_indices["EXP"]], "%d-%b-%y")
                except ValueError:
                    expiration_date = datetime.strptime(line[column_indices["EXP"]], "%m/%d/%y")
            part = GLILotInfo(description=line[column_indices["Description"]],
                              part_number=line[column_indices["Part_#"]],
                              tube_code=line[column_indices["TubeCode"]],
                              volume_remaining=Decimal(line[column_indices["Volume_Remaining"]]),
                              lot_number=line[column_indices["Lot"]],
                              expiration_date=expiration_date)
            if part.part_number not in parts:
                parts[part.part_number] = []
            parts[part.part_number].append(part)
        return InventoryTracking(parts=parts)
