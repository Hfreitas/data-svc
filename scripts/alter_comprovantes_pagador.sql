-- Idempotent: add PL payer/attended fields (+ canal_venda if missing) to comprovantes.
ALTER TABLE public.comprovantes ADD COLUMN IF NOT EXISTS canal_venda   text;
ALTER TABLE public.comprovantes ADD COLUMN IF NOT EXISTS pagador_nome  text;
ALTER TABLE public.comprovantes ADD COLUMN IF NOT EXISTS pagador_cpf   text;
ALTER TABLE public.comprovantes ADD COLUMN IF NOT EXISTS atendido_nome text;
