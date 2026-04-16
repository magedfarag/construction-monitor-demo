import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aoisApi } from "../api/client";
import type { CreateAoiRequest, Aoi } from "../api/types";

const AOIS_CACHE_KEY = "geoint:aois-cache";

function readAoisCache(): Aoi[] {
  try {
    const raw = localStorage.getItem(AOIS_CACHE_KEY);
    return raw ? (JSON.parse(raw) as Aoi[]) : [];
  } catch {
    return [];
  }
}

export function useAois() {
  const query = useQuery({
    queryKey: ["aois"],
    queryFn: aoisApi.list,
    placeholderData: readAoisCache,
  });

  // Keep localStorage in sync so the list is available instantly on next load.
  useEffect(() => {
    if (query.data) {
      try {
        localStorage.setItem(AOIS_CACHE_KEY, JSON.stringify(query.data));
      } catch { /* storage quota exceeded — ignore */ }
    }
  }, [query.data]);

  return query;
}

export function useAoi(id: string | null) {
  return useQuery({
    queryKey: ["aois", id],
    queryFn: () => aoisApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateAoi() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateAoiRequest) => aoisApi.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["aois"] }),
  });
}

export function useDeleteAoi() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => aoisApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["aois"] }),
  });
}