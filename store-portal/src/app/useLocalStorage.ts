import { useEffect, useState } from 'react'

export function useLocalStorageState<T>(
  key: string,
  defaultValue: T,
  options?: { serialize?: (value: T) => string; deserialize?: (raw: string) => T },
): [T, (next: T) => void] {
  const serialize = options?.serialize ?? ((v) => JSON.stringify(v))
  const deserialize = options?.deserialize ?? ((raw) => JSON.parse(raw) as T)

  const [value, setValue] = useState<T>(() => {
    try {
      const raw = window.localStorage.getItem(key)
      if (raw == null) return defaultValue
      return deserialize(raw)
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, serialize(value))
    } catch {
      // Ignore (private mode / storage disabled).
    }
  }, [key, serialize, value])

  return [value, setValue]
}
