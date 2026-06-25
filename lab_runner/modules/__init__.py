from lab_runner.modules.m02_linguistics import LinguisticsModule
from lab_runner.modules.m03_scale_101 import Scale101Module
from lab_runner.modules.m04_scale_201 import Scale201Module
from lab_runner.modules.m05_rag import RAGModule
from lab_runner.modules.m06_observability import ObservabilityModule
from lab_runner.modules.m07_guardrails import GuardrailsModule
from lab_runner.modules.m08_agents import AgentsModule
from lab_runner.modules.m09_onprem import OnPremModule
from lab_runner.modules.m10_model_optimization import ModelOptimizationModule
from lab_runner.modules.m11_maas import MaaSModule
from lab_runner.modules.m12_finetuning import FineTuningModule

MODULE_REGISTRY: dict[int, type] = {
    2: LinguisticsModule,
    3: Scale101Module,
    4: Scale201Module,
    5: RAGModule,
    6: ObservabilityModule,
    7: GuardrailsModule,
    8: AgentsModule,
    9: OnPremModule,
    10: ModelOptimizationModule,
    11: MaaSModule,
    12: FineTuningModule,
}
