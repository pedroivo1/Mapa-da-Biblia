-- Marcações de versículos: uma linha por versículo que a pessoa grifou ou salvou.
--   livro:     id do livro em compartilhado/dados/canon.json ("genesis", "joao"…)
--   grifo:     cor do grifo ("amarelo", "verde", "azul", "rosa") ou null
--   salvo:     true quando está na lista de versículos salvos (página /versiculos/)
--   temas:     temas em que foi salvo ("Fé", "Promessas"…); vazio = salvo sem tema
-- Quando o versículo perde o grifo e deixa de ser salvo, a linha é apagada.
create table public.marcacoes (
  user_id uuid not null references auth.users(id) on delete cascade,
  livro text not null,
  capitulo smallint not null,
  versiculo smallint not null,
  grifo text,
  salvo boolean not null default false,
  temas text[] not null default '{}'::text[],
  atualizado_em timestamptz not null default now(),
  primary key (user_id, livro, capitulo, versiculo),
  constraint marcacoes_grifo check (grifo is null or grifo in ('amarelo', 'verde', 'azul', 'rosa')),
  constraint marcacoes_algo check (grifo is not null or salvo)
);

alter table public.marcacoes enable row level security;

create policy "ler as próprias marcações" on public.marcacoes
  for select to authenticated using ((select auth.uid()) = user_id);

create policy "criar as próprias marcações" on public.marcacoes
  for insert to authenticated with check ((select auth.uid()) = user_id);

create policy "editar as próprias marcações" on public.marcacoes
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "apagar as próprias marcações" on public.marcacoes
  for delete to authenticated using ((select auth.uid()) = user_id);
