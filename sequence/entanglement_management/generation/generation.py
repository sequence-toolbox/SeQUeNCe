from .generation_a_bk import EntanglementGenerationBarretKokA
from .generation_b_bk import EntanglementGenerationBarretKokB
from .generation_a_sh import EntanglementGenerationSingleHeraldedA
from .generation_b_sh import EntanglementGenerationSingleHeraldedB
from .generation_message import EntanglementGenerationMessage, GenerationMsgType


class EntanglementGenerationProtocol:
    _protocols = {
        'BarretKokA': EntanglementGenerationBarretKokA,
        'BarretKokB': EntanglementGenerationBarretKokB,
        'SingleHeraldedA': EntanglementGenerationSingleHeraldedA,
        'SingleHeraldedB': EntanglementGenerationSingleHeraldedB
    }

    @classmethod
    def register(cls, name, *args, **kwargs):
        if name not in cls._protocols:
            raise ValueError(f"EG Protocol '{name}' is not registered.")
        return cls._protocols[name](*args, **kwargs)


    @staticmethod
    def create(protocol_type: str, *args, **kwargs):
        if protocol_type not in EntanglementGenerationProtocol._protocols:
            raise ValueError(f"Unknown EG protocol type: {protocol_type}")
        return EntanglementGenerationProtocol._protocols[protocol_type](*args, **kwargs)