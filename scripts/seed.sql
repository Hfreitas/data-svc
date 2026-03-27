INSERT INTO public.usuarios (
  numero_telefone, nome, razao_social, estado_atual,
  interacao_previa, tipo_negocio, data_primeiro_contato, data_ultimo_contato)
VALUES
  ('5511900000001', 'Dev Teste', 'Negocio Teste Ltda', 'menu',
   true, 'servico', NOW(), CURRENT_DATE),
  ('5511900000002', 'Maria Onboarding', 'Maria Costura', 'menu',
   false, null, NOW(), CURRENT_DATE)
ON CONFLICT DO NOTHING;

INSERT INTO public.comprovantes (
  usuario_id, item, quantidade, valor_unitario, valor_total,
  operacao, data_venda, item_hash)
SELECT u.id, 'Consultoria', 1, 500.00, 500.00, 'venda',
       CURRENT_DATE - 5, md5('consultoria-' || u.id::text)
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';

INSERT INTO public.comprovantes (
  usuario_id, item, quantidade, valor_unitario, valor_total,
  operacao, data_compra, item_hash)
SELECT u.id, 'Aluguel escritório', 1, 800.00, 800.00, 'gasto',
       CURRENT_DATE - 10, md5('aluguel-' || u.id::text)
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';

INSERT INTO public.agendamentos (
  usuario_id, nome_compromisso, data_compromisso,
  hora_compromisso, status, data_criacao, data_modificacao)
SELECT u.id, 'Reunião com cliente', CURRENT_DATE + 2,
       '14:00'::time, 'confirmado', NOW(), NOW()
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';
