import csv
import io
from typing import List, TypeVar, Union
from pydantic import BaseModel
from pathlib import Path

T = TypeVar("T", bound=BaseModel)


class CSVGenerator:
    @staticmethod
    def to_csv_string(
        data: List[T],
        include_header: bool = True,
        delimiter: str = ",",
    ) -> str:
        """
        Returns CSV-файл as str.
        """
        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=list(data[0].model_dump().keys()),
            delimiter=delimiter,
        )

        if include_header:
            writer.writeheader()

        for item in data:
            writer.writerow(item.model_dump())

        return output.getvalue()

    @staticmethod
    def save_to_file(
        data: List[T],
        file_path: Union[str, Path],
        include_header: bool = True,
        delimiter: str = ",",
        encoding: str = "utf-8-sig",
    ) -> Path:
        """
        Savings CSV as file.
        """
        if not data:
            raise ValueError("Clear data")

        path = Path(file_path)
        with path.open("w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(data[0].model_dump().keys()),
                delimiter=delimiter,
            )

            if include_header:
                writer.writeheader()

            for item in data:
                writer.writerow(item.model_dump())

        return path
