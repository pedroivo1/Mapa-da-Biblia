-- Progresso de leitura: uma linha por usuário, no mesmo formato que o biblia.js usa.
-- lido:       { "livro:gn": true, "rei:davi": true, "era:...": true }
-- versiculos: { "gn": { "1": 1, "2": [1, 2, 3] } }  (1 = capítulo inteiro)
create table public.progresso (
  user_id uuid primary key references auth.users(id) on delete cascade,
  lido jsonb not null default '{}'::jsonb,
  versiculos jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now()
);

alter table public.progresso enable row level security;

create policy "ler o próprio progresso" on public.progresso
  for select to authenticated using ((select auth.uid()) = user_id);

create policy "criar o próprio progresso" on public.progresso
  for insert to authenticated with check ((select auth.uid()) = user_id);

create policy "editar o próprio progresso" on public.progresso
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
