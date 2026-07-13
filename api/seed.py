"""
Seed: hierarchy levels, hierarchy nodes, users, product categories and products.
Run: docker compose exec api python -m api.seed
"""
import asyncio

from passlib.context import CryptContext
from sqlalchemy import select

from api.database import SessionLocal, engine
from api.models import Base
from api.models.accounts import User
from api.models.catalog import Product, ProductCategory
from api.models.hierarchy import HierarchyLevel, HierarchyNode

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_LEVELS = [
    {"name": "Gerente", "depth": 1, "prefix": "GER"},
    {"name": "Coordenador Regional", "depth": 2, "prefix": "REG"},
    {"name": "Coordenador Local", "depth": 3, "prefix": "COO"},
    {"name": "Supervisor", "depth": 4, "prefix": "SUP"},
    {"name": "Vendedor", "depth": 5, "prefix": "VEN"},
]

# (source_id, name, email, parent_source_id or None)
HIERARCHY_NODES = [
    # GERENTES
    ("GER_01", "FABIO SHAEN DE SOUZA", "fabio.shaen@belloalimentos.com.br", None),
    # REGIONAIS
    ("REG_01", "DIVINO REGINALDO RODRIGUES", "divino.rodrigues@belloalimentos.com.br", "GER_01"),
    ("REG_02", "MARCELO RODRIGUES CIRELI", "marcelo.rodrigues@belloalimentos.com.br", "GER_01"),
    # LOCAIS
    ("COO_01", "ALEXANDRE FERREIRA MENDONCA", "alexandre.ferreira@belloalimentos.com.br", "REG_02"),
    ("COO_02", "HIRAN EVERALDO DOS SANTOS", "hiran.santos@belloalimentos.com.br", "REG_02"),
    ("COO_03", "ELTON AGUERO COSTA", "elton.aguero@belloalimentos.com.br", "REG_01"),
    ("COO_04", "ANTONIO DA SILVA CAMPOS", "antonio.campos@belloalimentos.com.br", "REG_01"),
    ("COO_05", "EDVAN DA SILVA SOUZA", "edvan.souza@belloalimentos.com.br", "REG_02"),
    ("COO_06", "WILSON GIMENES", "wilson.gimenes@belloalimentos.com.br", "REG_02"),
    ("COO_07", "MARCELO RODRIGUES CIRELI", "marcelo.rodrigues@belloalimentos.com.br", "REG_02"),
    ("COO_08", "GELSON OCAMPOS", "gelson.ocampos@belloalimentos.com.br", "REG_01"),
    ("COO_09", "DIVINO REGINALDO RODRIGUES", "divino.rodrigues@belloalimentos.com.br", "REG_01"),
    # SUPERVISORES
    ("SUP_01", "IAGO RIBEIRO CALLIGURI", "iago.calliguri@belloalimentos.com.br", "COO_05"),
    ("SUP_02", "JOSIEL DOS SANTOS BARBOSA", "josiel.barbosa@belloalimentos.com.br", "COO_05"),
    ("SUP_03", "WAGNER SALMI CAETANO", "wagner.caetano@belloalimentos.com.br", "COO_05"),
    ("SUP_04", "SANDRO PEDROSO PORTUGAL", "sandro.silva@belloalimentos.com.br", "COO_03"),
    ("SUP_05", "RAFAEL MANZOTTI", "rafael.manzotti@belloalimentos.com.br", "COO_03"),
    ("SUP_06", "PERYS FERREIRA DOS SANTOS", "perys.santos@belloalimentos.com.br", "COO_03"),
    ("SUP_07", "ALESSANDRA COSTA DA SILVA", "alessandra.silva@belloalimentos.com.br", "COO_09"),
    ("SUP_08", "WISLEY SOUSA DE OLIVEIRA", "wisley.oliveira@belloalimentos.com.br", "COO_04"),
    ("SUP_09", "LUIZ HENRIQUE MARTINS GOUVEIA", "luiz.gouveia@belloalimentos.com.br", "COO_04"),
    ("SUP_10", "WAGNER WANDERSON DOS SANTOS", "wagner.santos@belloalimentos.com.br", "COO_02"),
    ("SUP_11", "FABRICIO HENRIQUE CRUZ ZANIN", "fabricio.zanin@belloalimentos.com.br", "COO_02"),
    ("SUP_12", "MARCELO DOS NASCIMENTO SANTOS", "marcelo.nascimento@belloalimentos.com.br", "COO_02"),
    ("SUP_13", "HUDSON ROSA SILVA", "hudson.silva@belloalimentos.com.br", "COO_02"),
    ("SUP_14", "AMARILDO LUIZ PEREIRA", "amarildo.pereira@belloalimentos.com.br", "COO_01"),
    ("SUP_15", "DIOGO LUIZ PEREIRA DE LIMA", "diogo.lima@belloalimentos.com.br", "COO_01"),
    ("SUP_16", "RAFAEL HENRIQUE BIANCHINI CARDOSO", "rafael.cardoso@belloalimentos.com.br", "COO_08"),
    ("SUP_17", "WILSON GIMENES", "wilson.gimenes.sup@belloalimentos.com.br", "COO_06"),
    ("SUP_19", "WEULER ALVES DA CUNHA", "weuler.cunha@belloalimentos.com.br", "COO_04"),
    ("SUP_20", "EMERSON RODRIGO DOS SANTOS VARELA", "emerson.varela@belloalimentos.com.br", "COO_07"),
    ("SUP_23", "FRANKLIN RICCELLE VILELA DE ALMEIDA", "franklin.riccelle@belloalimentos.com.br", "COO_09"),
    ("SUP_24", "RAMAO HELIO ALONSO FAUSTINO", "ramao.alonso@belloalimentos.com.br", "COO_07"),
    ("SUP_25", "RAFAEL RIBEIRO RAMOS", "rafael.ramos@belloalimentos.com.br", "COO_07"),
    ("SUP_26", "FABIANO RIBEIRO RAMOS", "fabiano.ramos@belloalimentos.com.br", "COO_07"),
    ("SUP_27", "GENIVALDO RIBEIRO SILVA", "genivaldo.silva@belloalimentos.com.br", "COO_07"),
    ("SUP_28", "KAIO CESAR COSTA FERREIRA", "kaio.ferreira@belloalimentos.com.br", "COO_07"),
    ("SUP_29", "WILLIAM MENDONCA DOS SANTOS", "william.santos@belloalimentos.com.br", "COO_01"),
    # VENDEDORES
    ("VEN_01", "MARCELO DA SILVA", "marcelo.silva@belloalimentos.com.br", "SUP_01"),
    ("VEN_02", "WAGNER SALMI CAETANO", "wagner.caetano.ven@belloalimentos.com.br", "SUP_03"),
    ("VEN_04", "MELQUIADES CARDOSO DOS SANTOS JUNIOR", "melquiades.santos@belloalimentos.com.br", "SUP_01"),
    ("VEN_06", "EDILSON PEREIRA DA SILVA", "edilson.silva@belloalimentos.com.br", "SUP_02"),
    ("VEN_07", "FERNANDO LIMA RIBEIRO", "fernando.lima@belloalimentos.com.br", "SUP_02"),
    ("VEN_08", "DIEFERSON FREITAS FERNANDES", "dieferson.fernandes@belloalimentos.com.br", "SUP_02"),
    ("VEN_09", "SILVONEY HERCULANO DA SILVA", "silvoney.silva@belloalimentos.com.br", "SUP_02"),
    ("VEN_10", "NATAIR MALTA NETO", "natair.neto@belloalimentos.com.br", "SUP_02"),
    ("VEN_100", "EMERSON RODRIGO DOS SANTOS VARELA", "emerson.varela.ven@belloalimentos.com.br", "SUP_20"),
    ("VEN_108", "PATRICIA DE OLIVEIRA", "patricia.oliveira@belloalimentos.com.br", "SUP_02"),
    ("VEN_112", "PAULO HENRIQUE PEDROSO DO NASCIMENTO", "paulo.nascimento@belloalimentos.com.br", "SUP_29"),
    ("VEN_12", "OSMAIR FERREIRA DA SILVA", "osmair.silva@belloalimentos.com.br", "SUP_04"),
    ("VEN_124", "LUIS HENRIQUE LOPES FAGUNDES", "luis.fagundes@belloalimentos.com.br", "SUP_08"),
    ("VEN_125", "SELIM ZOGAIB", "selim.zogaib@belloalimentos.com.br", "SUP_15"),
    ("VEN_126", "ERICKSON BERNAL DA SILVA", "erickson.bernal@belloalimentos.com.br", "SUP_15"),
    ("VEN_127", "RODRIGO MARTINS FRANCISCO DIAS", "rodrigo.dias@belloalimentos.com.br", "SUP_01"),
    ("VEN_129", "AGTA LIMA RODRIGUES BARBOSA", "agta.lima@belloalimentos.com.br", "SUP_08"),
    ("VEN_130", "CLEITON DUARTE NUNES", "cleiton.nunes@belloalimentos.com.br", "SUP_04"),
    ("VEN_131", "WILIAN REZENDE CONCEICAO", "wilian.rezende@belloalimentos.com.br", "SUP_29"),
    ("VEN_132", "MARCELO LAMERA", "marcelo.lamera@belloalimentos.com.br", "SUP_05"),
    ("VEN_137", "ELVIS LUNELLI", "elvis.lunelli@belloalimentos.com.br", "SUP_29"),
    ("VEN_138", "ARTHUR PEREIRA GOMES", "arthur.gomes@belloalimentos.com.br", "SUP_01"),
    ("VEN_139", "LUCIANO RIBEIRO RAMOS DUARTE", "luciano.duarte@belloalimentos.com.br", "SUP_01"),
    ("VEN_14", "KAROLINA DE KACIA SOROCA DOS SANTOS", "karolina.santos@belloalimentos.com.br", "SUP_04"),
    ("VEN_141", "GABRIEL FREITAS DE LIMA", "gabriel.freitas@belloalimentos.com.br", "SUP_16"),
    ("VEN_143", "GILMAR LEAL DE ARAUJO", "gilmar.leal@belloalimentos.com.br", "SUP_16"),
    ("VEN_15", "LEANDRO COSTA DA MATA", "leandro.mata@belloalimentos.com.br", "SUP_04"),
    ("VEN_16", "FELIPE HENRIQUE SILVA BEZERRA", "felipe.bezerra@belloalimentos.com.br", "SUP_04"),
    ("VEN_17", "WELISSON SILVA SANTOS", "welisson.santos@belloalimentos.com.br", "SUP_05"),
    ("VEN_18", "ARIEL BOETTCHER", "ariel.boettcher@belloalimentos.com.br", "SUP_05"),
    ("VEN_21", "MARCOS PREHL", "marcos.prehl@belloalimentos.com.br", "SUP_06"),
    ("VEN_22", "SERGIO SOARES BALEEIRO BOTELHO", "sergio.botelho@belloalimentos.com.br", "SUP_06"),
    ("VEN_23", "CELSON RODRIGUES DIAS DA SILVA", "celso.silva@belloalimentos.com.br", "SUP_06"),
    ("VEN_24", "THAIS ROCHA SOUZA", "thais.souza@belloalimentos.com.br", "SUP_06"),
    ("VEN_25", "JEFFERSON RODRIGUES NUNES", "jefferson.rodrigues@belloalimentos.com.br", "SUP_06"),
    ("VEN_27", "ROGERIO BRANDAO DE FREITAS", "rogerio.freitas@belloalimentos.com.br", "SUP_06"),
    ("VEN_28", "DUEINE DUTRA BORGES", "dueine.borges@belloalimentos.com.br", "SUP_08"),
    ("VEN_29", "GERALDINO PERES DA SILVA", "geraldino.peres@belloalimentos.com.br", "SUP_08"),
    ("VEN_30", "GILCIMAR BARROS DA SILVA", "gilcimar.silva@belloalimentos.com.br", "SUP_08"),
    ("VEN_32", "KARINA DA SILVA DIAS", "karina.alves@belloalimentos.com.br", "SUP_08"),
    ("VEN_34", "CLAUDIO CHAVES DE LIMA", "claudio.chaves@belloalimentos.com.br", "SUP_09"),
    ("VEN_35", "GUSTAVO PACHECO ALVES", "gustavo.pacheco@belloalimentos.com.br", "SUP_09"),
    ("VEN_36", "LUIS FELLIPE SILVA VITOR", "luis.vitor@belloalimentos.com.br", "SUP_09"),
    ("VEN_37", "MARYANA LEMBI GOMES", "maryana.gomes@belloalimentos.com.br", "SUP_09"),
    ("VEN_38", "WILTON ROSSI GONTIJO", "wilton.gontijo@belloalimentos.com.br", "SUP_09"),
    ("VEN_41", "WEULER ALVES DA CUNHA", "weuler.cunha.ven@belloalimentos.com.br", "SUP_19"),
    ("VEN_43", "ROGERIO FERREIRA DA SILVA", "rogerio.silva@belloalimentos.com.br", "SUP_10"),
    ("VEN_44", "UIL FERNANDEZ DOS SANTOS", "uil.santos@belloalimentos.com.br", "SUP_10"),
    ("VEN_45", "JOILSON DE BARROS LIMA", "joilson.barros@belloalimentos.com.br", "SUP_10"),
    ("VEN_46", "SERGIO CANDIDO REZENDE", "sergio.rezende@belloalimentos.com.br", "SUP_10"),
    ("VEN_47", "LEANDRO APARECIDO FERNANDES", "leandro.fernandes@belloalimentos.com.br", "SUP_10"),
    ("VEN_48", "REGINALDO BRASIL APARECIDO GARCIA", "reginaldo.garcia@belloalimentos.com.br", "SUP_11"),
    ("VEN_49", "AMARILDO ROSA PAREDES", "amarildo.paredes@belloalimentos.com.br", "SUP_11"),
    ("VEN_50", "FRANCISCO FERNANDEZ LOPES", "francisco.lopes@belloalimentos.com.br", "SUP_11"),
    ("VEN_51", "REGIANE RODRIGUES DA SILVA SANTOS", "regiane.santos@belloalimentos.com.br", "SUP_11"),
    ("VEN_52", "HUDSON ROSA SILVA", "hudson.silva.ven@belloalimentos.com.br", "SUP_11"),
    ("VEN_53", "TIAGO JOSE DAHER FEITOSA", "tiago.feitosa@belloalimentos.com.br", "SUP_11"),
    ("VEN_54", "ROGERIO APARECIDO CANHETE MARQUES", "rogerio.marques@belloalimentos.com.br", "SUP_12"),
    ("VEN_55", "JABES DE OLIVEIRA SILVA", "jabes.silva@belloalimentos.com.br", "SUP_12"),
    ("VEN_56", "MOISES DA SILVA ABREU", "moises.silva@belloalimentos.com.br", "SUP_10"),
    ("VEN_57", "LUIS CARLOS DEMARCHI DE OLIVEIRA", "luis.demarchi@belloalimentos.com.br", "SUP_12"),
    ("VEN_58", "MAURO ALEXANDRE PRADO DA CONCEICAO", "mauro.prado@belloalimentos.com.br", "SUP_12"),
    ("VEN_59", "WEULLER GOMES RODRIGUES GUIMARAES", "weuller.gomes@belloalimentos.com.br", "SUP_12"),
    ("VEN_60", "JONATHAS GOMES DA SILVA", "jonathas.silva@belloalimentos.com.br", "SUP_12"),
    ("VEN_62", "AGAZILDO DOS SANTOS OLIVEIRA", "agazildo.oliveira@belloalimentos.com.br", "SUP_13"),
    ("VEN_63", "VINICIUS OHARA RAMIRES SOARES", "vinicius.ramires@belloalimentos.com.br", "SUP_17"),
    ("VEN_64", "GEOVANI DA SILVA LANG", "geovani.silva@belloalimentos.com.br", "SUP_14"),
    ("VEN_65", "RAMON JUNGLOS DA SILVA", "ramon.silva@belloalimentos.com.br", "SUP_14"),
    ("VEN_66", "LUCAS FURTADO CORREIA", "lucas.correia@belloalimentos.com.br", "SUP_14"),
    ("VEN_67", "GUSTAVO DE OLIVEIRA AQUINO", "gustavo.aquino@belloalimentos.com.br", "SUP_15"),
    ("VEN_68", "MARCIO BARRETO VERISSIMO", "marcio.verissimo@belloalimentos.com.br", "SUP_14"),
    ("VEN_70", "JOSE OLMEDO DE SOUZA JUNIOR", "jose.souza@belloalimentos.com.br", "SUP_14"),
    ("VEN_71", "ROBERTO ARIEL NOTARIO", "roberto.notario@belloalimentos.com.br", "SUP_15"),
    ("VEN_72", "BARBARA FINCK", "barbara.finck@belloalimentos.com.br", "SUP_29"),
    ("VEN_75", "JOSE DO PRADO ALMEIDA", "jose.almeida@belloalimentos.com.br", "SUP_15"),
    ("VEN_76", "JOAO CARLOS DE OLIVEIRA SILVA", "joao.silva@belloalimentos.com.br", "SUP_29"),
    ("VEN_77", "KAIO CESAR COSTA FERREIRA", "kaio.ferreira.ven@belloalimentos.com.br", "SUP_28"),
    ("VEN_79", "GENIVALDO PEREIRA RODRIGUES", "genivaldo.rodrigues@belloalimentos.com.br", "SUP_16"),
    ("VEN_80", "ANDERSON FERREIRA DE SOUZA", "anderson.souza@belloalimentos.com.br", "SUP_16"),
    ("VEN_81", "BRUNO RAMOS DA SILVA", "bruno.silva@belloalimentos.com.br", "SUP_16"),
    ("VEN_83", "CAIO VINICIUS VIEIRA", "caio.vieira@belloalimentos.com.br", "SUP_16"),
    ("VEN_84", "GRACIANO SANTOS MUNIZ", "graciano.muniz@belloalimentos.com.br", "SUP_16"),
    ("VEN_85", "JOSE FERREIRA DE MELO FILHO", "jose.filho@belloalimentos.com.br", "SUP_16"),
    ("VEN_87", "RAMAO HELIO ALONSO FAUSTINO", "ramao.alonso.ven@belloalimentos.com.br", "SUP_24"),
    ("VEN_88", "RAFAEL RIBEIRO RAMOS", "rafael.ramos.ven@belloalimentos.com.br", "SUP_25"),
    ("VEN_89", "FRANKLIN RICCELLE VILELA DE ALMEIDA", "franklin.riccelle.ven@belloalimentos.com.br", "SUP_23"),
    ("VEN_90", "FABIANO RIBEIRO RAMOS", "fabiano.ramos.ven@belloalimentos.com.br", "SUP_26"),
    ("VEN_91", "GENIVALDO RIBEIRO SILVA", "genivaldo.silva.ven@belloalimentos.com.br", "SUP_27"),
    ("VEN_92", "GUTEMBERG LOPES AQUINO", "gutemberg.aquino@belloalimentos.com.br", "SUP_17"),
    ("VEN_93", "FLAVIO ALEXSANDER OLIVEIRA CRUZ", "flavio.cruz@belloalimentos.com.br", "SUP_06"),
    ("VEN_94", "ALLYSON FABIO BARBOSA DA SILVA", "allyson.silva@belloalimentos.com.br", "SUP_05"),
    ("VEN_95", "ALESSANDRA COSTA DA SILVA", "alessandra.silva.ven@belloalimentos.com.br", "SUP_07"),
    ("VEN_98", "PATRICK SANTANA GONCALVES", "patrick.goncalves@belloalimentos.com.br", "SUP_13"),
]

CATEGORIES_AND_PRODUCTS = {
    "GRP_01": {
        "name": "EMBUTIDOS",
        "products": [
            ("PRO_01", "DEFUMADOS BELLO"), ("PRO_02", "DEFUMADOS TERCEIRO"),
            ("PRO_03", "DESFIADOS"), ("PRO_157", "EMBUTIDOS"),
            ("PRO_04", "EMBUTIDOS - PRESUNTO - BELLO"), ("PRO_05", "EMBUTIDOS CALABRESA"),
            ("PRO_150", "EMBUTIDOS LANCHE"), ("PRO_06", "EMBUTIDOS LINGUICA"),
            ("PRO_07", "EMBUTIDOS LINGUICA DE FRANGO"), ("PRO_149", "EMBUTIDOS MORTADELA"),
            ("PRO_08", "EMBUTIDOS SALSICHA"), ("PRO_09", "FATIADOS"),
            ("PRO_10", "LOMBO SUINO"),
        ],
    },
    "GRP_02": {
        "name": "FRANGOS",
        "products": [
            ("PRO_11", "ASA"), ("PRO_12", "ASA PORCIONADA COXINHA DA ASA"),
            ("PRO_13", "ASA PORCIONADA IQF COXINHA DA ASA"), ("PRO_14", "ASA PORCIONADA IQF MEIO DA ASA"),
            ("PRO_15", "ASA PORCIONADA MEIO DA ASA"), ("PRO_148", "ASA PORCIONADA TEMPERADA"),
            ("PRO_16", "ASA PORCIONADA TEMPERADA COXINHA DA ASA"), ("PRO_17", "ASA PORCIONADA TEMPERADA MEIO DA ASA"),
            ("PRO_18", "CARTILAGENS"), ("PRO_19", "CMS"), ("PRO_20", "CORACAO"), ("PRO_21", "DORSO"),
            ("PRO_22", "FGO INTEIRO S/ MIUDOS"), ("PRO_23", "FIGADO"),
            ("PRO_24", "FRANGO A PASSARINHO"), ("PRO_25", "FRANGO A PASSARINHO IQF"),
            ("PRO_26", "FRANGO A PASSARINHO TEMPERADO"), ("PRO_27", "FRANGO INTEIRO"),
            ("PRO_28", "FRANGO INTEIRO TEMPERADO"), ("PRO_29", "GALINHA IN NAT."),
            ("PRO_156", "GALINHA INTEIRA C/ MIUDOS"), ("PRO_30", "GALO IN NAT"),
            ("PRO_31", "KIT-FRANGO INTEIRO TEMPERADO"), ("PRO_32", "MEDALHAO"),
            ("PRO_33", "MEIO PEITO S/O S/P S/F IQF"), ("PRO_34", "MEIO PEITO S/O S/P TEMPERADO"),
            ("PRO_35", "MEIO PEITO SEM OSSO SEM PELE SEM FILEZINHO"), ("PRO_36", "MOELA"),
            ("PRO_37", "PEITO"), ("PRO_38", "PEITO SEM OSSO SEM PELE"),
            ("PRO_39", "PEITO SEM OSSO SEM PELE - CUBO"), ("PRO_40", "PEITO TEMPERADO"),
            ("PRO_41", "PELE"), ("PRO_42", "PERNA"), ("PRO_43", "PERNA DESOSSADA"),
            ("PRO_44", "PERNA LEG QUARTER"), ("PRO_45", "PERNA LEG QUARTER TEMPERADA"),
            ("PRO_46", "PERNA PORCIONADA"), ("PRO_47", "PERNA PORCIONADA IQF"),
            ("PRO_48", "PERNA PORCIONADA TEMPERADA"), ("PRO_49", "PERNA TEMPERADA"),
            ("PRO_50", "PESCOCO"), ("PRO_51", "PESCOCO SEM PELE"), ("PRO_52", "PEZINHO"),
            ("PRO_53", "PONTA DA ASA"), ("PRO_54", "REFILE"), ("PRO_55", "SAMBIQUIRA"),
            ("PRO_56", "SASSAMI"), ("PRO_57", "SASSAMI IQF"), ("PRO_58", "SASSAMI TEMPERADO"),
            ("PRO_126", "SHAWARMA"),
        ],
    },
    "GRP_03": {
        "name": "PESCADOS",
        "products": [
            ("PRO_63", "BACALHAU"), ("PRO_64", "CMS DE PEIXE"),
            ("PRO_65", "COSTELA DE TAMBAQUI"), ("PRO_66", "FILE DE TILAPIA"),
            ("PRO_67", "ISCA DE PEIXE"), ("PRO_152", "PACU/TAMBATINGA"),
            ("PRO_68", "PEIXE"), ("PRO_69", "PEIXE TERCEIRO"), ("PRO_154", "PESCADO"),
            ("PRO_70", "PINTADO"), ("PRO_71", "POLACA ALASCA"), ("PRO_72", "POSTA DE PINTADO"),
            ("PRO_153", "POSTA DE PIRAMUTABA"), ("PRO_151", "POSTA DE TAMBAQUI"),
            ("PRO_73", "POSTA DE TILAPIA"), ("PRO_74", "REVENDA INDUSTRIALIZADOS"),
            ("PRO_75", "SARDINHA"), ("PRO_76", "TAMBAQUI"), ("PRO_155", "TAMBATINGA"),
            ("PRO_77", "TILAPIA"),
        ],
    },
    "GRP_04": {
        "name": "REVENDA",
        "products": [
            ("PRO_127", "ACEM BOVINO - CUBOS"), ("PRO_139", "ALMONDEGAS"),
            ("PRO_78", "ANEIS DE CEBOLA"), ("PRO_79", "APRESUNTADO TERCEIRO"),
            ("PRO_80", "BARRIGA SUINA"), ("PRO_81", "BATATA CONGELADA"),
            ("PRO_82", "BISTECA SUINA"), ("PRO_83", "BOVINO INDUSTRIALIZADO"),
            ("PRO_84", "BOVINOS"), ("PRO_130", "CAMARAO"), ("PRO_159", "CARNE"),
            ("PRO_140", "CARNE MOIDA BOVINA"), ("PRO_85", "CARRE SUINO"),
            ("PRO_86", "COSTELA SUINA"), ("PRO_132", "EMBUTIDOS APRESUNTADO"),
            ("PRO_87", "EMBUTIDOS TERCEIRO"), ("PRO_88", "EMPANADOS"),
            ("PRO_133", "ESPINHACO SUINO"), ("PRO_89", "FILE SUINO"),
            ("PRO_90", "FOLHADOS REVENDA"), ("PRO_91", "FRANGO INTEIRO REVENDA"),
            ("PRO_92", "GORDURA"), ("PRO_93", "HAMBURGUER"),
            ("PRO_141", "KIT EMBUTIDO LINGUICA"), ("PRO_134", "KIT FATIADOS"),
            ("PRO_94", "KIT LOMBO"), ("PRO_142", "KIT-ASA PORCIONADA TEMPERADA MEIO DA ASA"),
            ("PRO_143", "KIT-CORACAO"), ("PRO_135", "KIT-DEFUMADOS BELLO"),
            ("PRO_95", "KIT-EMBUTIDOS LINGUICA DE FRANGO"), ("PRO_144", "KIT-MEDALHAO"),
            ("PRO_96", "LASANHA INDUSTRIALIZADO"), ("PRO_136", "LOMBO TEMPERADO"),
            ("PRO_97", "MANDIOCA IN NATURA"), ("PRO_98", "MEIO PEITO REVENDA"),
            ("PRO_99", "OVINOS"), ("PRO_100", "PALETA SUINA"),
            ("PRO_101", "PAO DE ALHO"), ("PRO_102", "PAO DE QUEIJO"),
            ("PRO_145", "PATINHO BOVINO"), ("PRO_103", "PEITO REVENDA"),
            ("PRO_138", "PEITO SEM OSSO COM PELE"), ("PRO_104", "PERNIL SUINO"),
            ("PRO_105", "PRESUNTO TERCEIRO"), ("PRO_106", "PRODUTOS SALGADOS"),
            ("PRO_107", "QUEIJOS"), ("PRO_108", "RAQUETE FGO TEMP REVENDA"),
            ("PRO_137", "REVENDA CORACAO"), ("PRO_109", "REVENDA COXINHA DAS ASAS"),
            ("PRO_110", "REVENDA FGO A PASSARINHO TEMP"), ("PRO_111", "REVENDA FILE COXA SCOXA"),
            ("PRO_112", "REVENDA FRANGO"), ("PRO_146", "REVENDA FRANGO A PASSARINHO IQF"),
            ("PRO_113", "REVENDA GALINHA INTEIRA"), ("PRO_114", "REVENDA MEIO DA ASA"),
            ("PRO_115", "REVENDA MEIO DA ASA IQF"), ("PRO_116", "REVENDA MEIO DA ASA PCT"),
            ("PRO_117", "REVENDA PERNA"), ("PRO_118", "REVENDA PERNA PORCIONADA"),
            ("PRO_119", "REVENDA SASSAMI"), ("PRO_120", "SALGADOS SUINOS"),
            ("PRO_121", "SOBREPALETA SUINA"), ("PRO_158", "SORVETE"),
            ("PRO_147", "SUINOS"), ("PRO_122", "TEMPERADOS SUINOS"),
            ("PRO_123", "TOUCINHO"), ("PRO_124", "VEGETAIS"),
            ("PRO_125", "WAFFLE REVENDA"),
        ],
    },
}

ROLE_BY_PREFIX = {
    "GER": "GERENTE",
    "REG": "COORDENADOR_REGIONAL",
    "COO": "COORDENADOR_LOCAL",
    "SUP": "SUPERVISOR",
    "VEN": "VENDEDOR",
}

ROLE_PRIORITY = {
    "GERENTE": 1,
    "COORDENADOR_REGIONAL": 2,
    "COORDENADOR_LOCAL": 3,
    "SUPERVISOR": 4,
    "VENDEDOR": 5,
}


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # 1. Hierarchy levels
        level_by_prefix = {}
        for level_data in DEFAULT_LEVELS:
            result = await db.execute(
                select(HierarchyLevel).where(HierarchyLevel.prefix == level_data["prefix"])
            )
            level = result.scalar_one_or_none()
            if not level:
                level = HierarchyLevel(**level_data)
                db.add(level)
                await db.flush()
                print(f"  + Nivel: {level_data['name']}")
            level_by_prefix[level_data["prefix"]] = level

        # 2. Hierarchy nodes (two passes: create, then set parents)
        node_by_source = {}
        for source_id, name, email, parent_sid in HIERARCHY_NODES:
            result = await db.execute(
                select(HierarchyNode).where(HierarchyNode.source_id == source_id)
            )
            node = result.scalar_one_or_none()
            if not node:
                prefix = source_id.split("_")[0]
                level = level_by_prefix[prefix]
                node = HierarchyNode(
                    level_id=level.id,
                    source_id=source_id,
                    name=name,
                )
                db.add(node)
                await db.flush()
            node_by_source[source_id] = node

        for source_id, name, email, parent_sid in HIERARCHY_NODES:
            if parent_sid and parent_sid in node_by_source:
                node_by_source[source_id].parent_id = node_by_source[parent_sid].id

        await db.flush()

        counts = {}
        for sid in node_by_source:
            prefix = sid.split("_")[0]
            counts[prefix] = counts.get(prefix, 0) + 1
        for prefix, count in sorted(counts.items()):
            print(f"  + {level_by_prefix[prefix].name}: {count} nos")

        # 3. Users (one per unique email, highest role as scope)
        email_to_best = {}
        for source_id, name, email, _ in HIERARCHY_NODES:
            prefix = source_id.split("_")[0]
            role = ROLE_BY_PREFIX[prefix]
            priority = ROLE_PRIORITY[role]
            node = node_by_source[source_id]

            if email not in email_to_best or priority < email_to_best[email]["priority"]:
                email_to_best[email] = {
                    "name": name,
                    "role": role,
                    "priority": priority,
                    "node_id": node.id,
                }

        user_count = 0
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            db.add(User(
                email="admin@bello.com.br",
                username="admin",
                hashed_password=pwd_context.hash("admin"),
                full_name="Administrador",
                role="ADMINISTRADOR",
            ))
            user_count += 1

        for email, info in sorted(email_to_best.items()):
            result = await db.execute(select(User).where(User.email == email))
            if not result.scalar_one_or_none():
                username = email.split("@")[0]
                db.add(User(
                    email=email,
                    username=username,
                    hashed_password=pwd_context.hash("bello2026"),
                    full_name=info["name"],
                    role=info["role"],
                    scope_node_id=info["node_id"],
                ))
                user_count += 1

        print(f"  + Users: {user_count} criados (senha padrao: bello2026)")

        # 4. Product categories and products
        for cat_source_id, cat_data in CATEGORIES_AND_PRODUCTS.items():
            result = await db.execute(
                select(ProductCategory).where(ProductCategory.source_id == cat_source_id)
            )
            category = result.scalar_one_or_none()
            if not category:
                category = ProductCategory(source_id=cat_source_id, name=cat_data["name"])
                db.add(category)
                await db.flush()

            for prod_source_id, prod_name in cat_data["products"]:
                result = await db.execute(
                    select(Product).where(Product.source_id == prod_source_id)
                )
                if not result.scalar_one_or_none():
                    db.add(Product(
                        category_id=category.id,
                        source_id=prod_source_id,
                        name=prod_name,
                    ))
            print(f"  + {cat_data['name']}: {len(cat_data['products'])} produtos")

        await db.commit()

        total_nodes = len(HIERARCHY_NODES)
        total_products = sum(len(c["products"]) for c in CATEGORIES_AND_PRODUCTS.values())
        print(f"\nSeed concluido:")
        print(f"  {total_nodes} nos de hierarquia")
        print(f"  {len(email_to_best) + 1} usuarios")
        print(f"  {len(CATEGORIES_AND_PRODUCTS)} categorias, {total_products} produtos")


if __name__ == "__main__":
    asyncio.run(seed())
