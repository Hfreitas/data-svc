-- DAS do perfil (valor oficial — nunca inventado pelo LLM)
-- Faixas 2026: comercio=82.05 | servicos=86.05 | comercio_servicos=87.05
ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS das_categoria text,
  ADD COLUMN IF NOT EXISTS das_valor numeric(10, 2);

COMMENT ON COLUMN public.usuarios.das_categoria IS
  'comercio | servicos | comercio_servicos — categoria fiscal do DAS-MEI';
COMMENT ON COLUMN public.usuarios.das_valor IS
  'Valor mensal do DAS (ex. 82.05). Fonte de verdade para Agente Dúvidas.';
