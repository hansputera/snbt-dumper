from dataclasses import dataclass


@dataclass
class SnbtRecord:
    utbk_no: str
    name: str
    date_of_birth: str
    bidik_misi: int
    passed: int
    ptn: str
    ptn_code: int
    prodi: str
    prodi_code: int
    next_url: str

    @classmethod
    def from_dict(cls, data: dict) -> 'SnbtRecord':
        return cls(
            utbk_no=data['no'],
            name=data['na'],
            date_of_birth=data['dob'],
            bidik_misi=int(data['bm']),
            passed=int(data['ac']),
            ptn=data['npt'],
            ptn_code=int(data['kpt']),
            prodi=data['nps'],
            prodi_code=int(data['kps']),
            next_url=data['upt'],
        )

    def to_csv_row(self) -> list[str]:
        return [
            self.utbk_no,
            self.name,
            self.date_of_birth,
            str(self.bidik_misi),
            str(self.passed),
            self.ptn,
            str(self.ptn_code),
            self.prodi,
            str(self.prodi_code),
            self.next_url,
        ]

    def to_db_tuple(self) -> tuple:
        return (
            self.utbk_no,
            self.name,
            self.date_of_birth,
            self.bidik_misi,
            self.passed,
            self.ptn,
            self.ptn_code,
            self.prodi,
            self.prodi_code,
            self.next_url,
        )
