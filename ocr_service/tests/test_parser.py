from app import parse_ktp


def test_parse_ktp_core_fields() -> None:
    result = parse_ktp(
        [
            "PROVINSI JAWA BARAT",
            "NIK : 3273010101900001",
            "Nama : BUDI SANTOSO",
            "Tempat/Tgl Lahir BANDUNG, 01-01-1990",
            "Alamat JL MERDEKA NO 1",
            "Pekerjaan WIRASWASTA",
        ],
        [0.98, 0.99, 0.97],
    )
    assert result["nik"] == "3273010101900001"
    assert result["nama"] == "BUDI SANTOSO"
    assert result["tempat_lahir"] == "BANDUNG"
    assert result["tanggal_lahir"] == "01-01-1990"
    assert result["alamat"] == "JL MERDEKA NO 1"
    assert result["confidence"] == 0.98


def test_parse_ktp_labels_split_from_values() -> None:
    result = parse_ktp(
        ["NIK", "3273010101900001", "NAMA", "SITI RAHMA", "TEMPAT/TGL LAHIR", "GARUT, 02-02-1992"]
    )
    assert result["nik"] == "3273010101900001"
    assert result["nama"] == "SITI RAHMA"
    assert result["tempat_lahir"] == "GARUT"
    assert result["tanggal_lahir"] == "02-02-1992"


def test_parse_ktp_header_city_and_address_components() -> None:
    result = parse_ktp(
        [
            "PROVINSI DKI JAKARTA",
            "JAKARTA BARAT",
            "NIK : 3171234567890123",
            "Alamat : JL. PASTI CEPAT A7/66",
            "RT/RW : 007/008",
            "Kel/Desa : PEGADUNGAN",
            "Kecamatan : KALIDERES",
        ]
    )
    assert result["provinsi"] == "DKI JAKARTA"
    assert result["kabupaten_kota"] == "JAKARTA BARAT"
    assert result["rt_rw"] == "007/008"
    assert result["kelurahan_desa"] == "PEGADUNGAN"
    assert result["kecamatan"] == "KALIDERES"

