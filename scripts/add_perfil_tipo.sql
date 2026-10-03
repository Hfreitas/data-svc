-- Perfil do fluxo (2 Pivôs): MEI/Autônomo vs Profissional Liberal
ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS perfil_tipo text,
  ADD COLUMN IF NOT EXISTS eh_mei boolean;

COMMENT ON COLUMN public.usuarios.perfil_tipo IS
  'mei | autonomo | profissional_liberal — escolhe Pivô MEI vs Pivô PL';
COMMENT ON COLUMN public.usuarios.eh_mei IS
  'true se perfil_tipo=mei; false para autonomo/profissional_liberal';

-- Opcional: índice para filtros/analytics
CREATE INDEX IF NOT EXISTS idx_usuarios_perfil_tipo
  ON public.usuarios (perfil_tipo)
  WHERE perfil_tipo IS NOT NULL;
