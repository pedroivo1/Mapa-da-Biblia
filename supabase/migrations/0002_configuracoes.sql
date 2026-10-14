-- Configurações da pessoa, uma linha por usuário. O formato é livre (jsonb) e o site mescla por chave:
--   linha_do_tempo: { "desktop": filtros, "mobile": filtros }  filtros das colunas e dos livros
--   plano:          { "padrao": id do plano, "pos": { "id do plano": "livro/cap" } }
--   leitor:         { "livro": id, "cap": n, "tam": tamanho da letra }
--   tema:           "light" | "dark"
create table public.configuracoes (
  user_id uuid primary key references auth.users(id) on delete cascade,
  dados jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now()
);

alter table public.configuracoes enable row level security;

create policy "ler as próprias configurações" on public.configuracoes
  for select to authenticated using ((select auth.uid()) = user_id);

create policy "criar as próprias configurações" on public.configuracoes
  for insert to authenticated with check ((select auth.uid()) = user_id);

create policy "editar as próprias configurações" on public.configuracoes
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
