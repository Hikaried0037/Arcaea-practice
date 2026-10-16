package moe.practice;

import org.json.*;
import java.util.*;

/** Catalog operations are independent of views and retain all unknown metadata. */
final class LibraryCatalog {
    final JSONObject songs, packs;
    LibraryCatalog(JSONObject songs, JSONObject packs) throws JSONException {
        this.songs=songs; this.packs=packs;
        songs.getJSONArray("songs"); packs.getJSONArray("packs");
    }
    static String pretty(JSONObject value) throws JSONException {StringBuilder out=new StringBuilder();format(value,out,0);return out.append('\n').toString();}
    private static void indent(StringBuilder out,int depth){for(int i=0;i<depth*4;i++)out.append(' ');}
    private static Iterator<String> orderedKeys(JSONObject object) {
        LinkedHashSet<String> keys=new LinkedHashSet<>();String[] preferred={};
        if(object.has("songs"))preferred=new String[]{"songs"};
        else if(object.has("packs"))preferred=new String[]{"packs","practice_sections"};
        else if(object.has("difficulties"))preferred=new String[]{"idx","id","title_localized","artist","search_title","search_artist","bpm","bpm_base","set","purchase","audioPreview","audioPreviewEnd","side","bg","bg_inverse","date","version","difficulties"};
        else if(object.has("ratingClass"))preferred=new String[]{"ratingClass","chartDesigner","jacketDesigner","rating","ratingPlus","date","version"};
        for(String key:preferred)if(object.has(key))keys.add(key);
        Iterator<String> rest=object.keys();while(rest.hasNext())keys.add(rest.next());return keys.iterator();
    }
    private static void format(Object value,StringBuilder out,int depth)throws JSONException {
        if(value instanceof JSONObject){
            JSONObject object=(JSONObject)value;out.append('{');Iterator<String> keys=orderedKeys(object);boolean first=true;
            while(keys.hasNext()){String key=keys.next();if(!first)out.append(',');out.append('\n');indent(out,depth+1);out.append(JSONObject.quote(key)).append(": ");format(object.get(key),out,depth+1);first=false;}
            if(!first){out.append('\n');indent(out,depth);}out.append('}');
        }else if(value instanceof JSONArray){
            JSONArray array=(JSONArray)value;out.append('[');for(int i=0;i<array.length();i++){if(i>0)out.append(',');out.append('\n');indent(out,depth+1);format(array.get(i),out,depth+1);}if(array.length()>0){out.append('\n');indent(out,depth);}out.append(']');
        }else if(value==null||value==JSONObject.NULL)out.append("null");
        else if(value instanceof Number)out.append(JSONObject.numberToString((Number)value));
        else if(value instanceof Boolean)out.append(value.toString());
        else out.append(JSONObject.quote(value.toString()));
    }
    static String title(JSONObject value) {
        JSONObject n=value.optJSONObject("name_localized");
        if(n==null)n=value.optJSONObject("title_localized");
        if(n!=null)for(String language:new String[]{"zh-Hans","zh-Hant","en","ja"}) {
            String s=n.optString(language,"");if(!s.isEmpty())return s;
        }
        return value.optString("id","");
    }
    LinkedHashMap<String,String> sections() throws JSONException {
        LinkedHashMap<String,String> result=new LinkedHashMap<>();
        JSONArray definitions=packs.optJSONArray("practice_sections");
        if(definitions!=null)for(int i=0;i<definitions.length();i++) {
            JSONObject s=definitions.getJSONObject(i);result.put(s.getString("id"),title(s));
        }
        JSONArray a=packs.getJSONArray("packs");
        for(int i=0;i<a.length();i++){String id=a.getJSONObject(i).optString("section","arcaea");if(!result.containsKey(id))result.put(id,sectionTitle(id));}
        return result;
    }
    static String sectionTitle(String id) {
        switch(id){case "arcaea":return "Arcaea";case "mainstory":return "主线故事";case "sidestory":return "支线故事";
        case "collab":case "collaboration":return "联动曲包";case "mainstory2":return "主线故事 II";case "variety":return "曲风精选";case "shortstory":return "短篇故事";case "extend":return "World Extend";case "customize":return "自定义";default:return id;}
    }
    String addSection(String name) throws JSONException {
        JSONArray a=packs.optJSONArray("practice_sections");if(a==null){a=new JSONArray();packs.put("practice_sections",a);}
        String id="practice_"+UUID.randomUUID().toString().replace("-","");
        a.put(new JSONObject().put("id",id).put("name_localized",new JSONObject().put("en",name)));return id;
    }
    JSONObject findPack(String id) throws JSONException {
        JSONArray a=packs.getJSONArray("packs");for(int i=0;i<a.length();i++)if(a.getJSONObject(i).optString("id").equals(id))return a.getJSONObject(i);return null;
    }
    int songCount(Set<String> ids) throws JSONException {
        int n=0;JSONArray a=songs.getJSONArray("songs");for(int i=0;i<a.length();i++)if(ids.contains(a.getJSONObject(i).optString("set","base")))n++;return n;
    }
    Set<String> descendants(String id) throws JSONException {
        LinkedHashSet<String> ids=new LinkedHashSet<>();ids.add(id);JSONArray a=packs.getJSONArray("packs");boolean added;
        do{added=false;for(int i=0;i<a.length();i++){JSONObject p=a.getJSONObject(i);if(ids.contains(p.optString("pack_parent","")))added|=ids.add(p.getString("id"));}}while(added);
        return ids;
    }
    void deleteSong(String id) throws JSONException {
        JSONArray a=songs.getJSONArray("songs"),out=new JSONArray();for(int i=0;i<a.length();i++)if(!a.getJSONObject(i).getString("id").equals(id))out.put(a.getJSONObject(i));songs.put("songs",out);
    }
    void deletePacks(Set<String> ids, boolean deleteSongs) throws JSONException {
        JSONArray a=packs.getJSONArray("packs"),remaining=new JSONArray();for(int i=0;i<a.length();i++)if(!ids.contains(a.getJSONObject(i).getString("id")))remaining.put(a.getJSONObject(i));
        JSONArray tracks=songs.getJSONArray("songs"),out=new JSONArray();String destination=null;
        if(!deleteSongs&&songCount(ids)>0){
            for(int i=0;i<remaining.length();i++)if(remaining.getJSONObject(i).getString("id").equals("base"))destination="base";
            if(destination==null){destination="practice_unfiled";boolean exists=false;for(int i=0;i<remaining.length();i++)exists|=destination.equals(remaining.getJSONObject(i).getString("id"));
                if(!exists)remaining.put(newPack(destination,"未分类歌曲","arcaea"));}
        }
        for(int i=0;i<tracks.length();i++){JSONObject song=tracks.getJSONObject(i);if(ids.contains(song.optString("set","base"))){if(deleteSongs)continue;song.put("set",destination);}out.put(song);}
        packs.put("packs",remaining);songs.put("songs",out);
    }
    void deleteSection(String id,boolean deleteContents) throws JSONException {
        JSONArray a=packs.getJSONArray("packs");Set<String> ids=new LinkedHashSet<>();
        for(int i=0;i<a.length();i++)if(a.getJSONObject(i).optString("section","arcaea").equals(id))ids.addAll(descendants(a.getJSONObject(i).getString("id")));
        if(deleteContents)deletePacks(ids,true);else {
            String destination="arcaea".equals(id)?addSection("未分类曲包"):"arcaea";
            for(int i=0;i<a.length();i++)if(ids.contains(a.getJSONObject(i).getString("id")))a.getJSONObject(i).put("section",destination);
        }
        JSONArray defs=packs.optJSONArray("practice_sections"),out=new JSONArray();if(defs!=null)for(int i=0;i<defs.length();i++)if(!defs.getJSONObject(i).getString("id").equals(id))out.put(defs.getJSONObject(i));packs.put("practice_sections",out);
    }
    static JSONObject newPack(String id,String name,String section) throws JSONException {
        return new JSONObject().put("id",id).put("section",section).put("plus_character",-1).put("cost",0)
            .put("is_extend_pack",false).put("name_localized",new JSONObject().put("en",name))
            .put("description_localized",new JSONObject().put("en",""));
    }
    JSONObject runtimePacks() throws JSONException {
        // The native renderer has a fixed section enum. Custom sections are displayed
        // by the live library page; keep their packs reachable in native All Songs.
        JSONObject copy=new JSONObject(packs.toString());copy.remove("practice_sections");JSONArray a=copy.getJSONArray("packs");
        Set<String> builtins=new HashSet<>(Arrays.asList("arcaea","mainstory","mainstory2","sidestory","collab","variety","collaboration","shortstory","extend","customize"));
        for(int i=0;i<a.length();i++){JSONObject p=a.getJSONObject(i);if(!builtins.contains(p.optString("section","arcaea")))p.put("section","arcaea");}
        return copy;
    }
    static float[] coverRect(int sw,int sh,int tw,int th) {
        float scale=Math.max(tw/(float)sw,th/(float)sh);float w=sw*scale,h=sh*scale;
        return new float[]{(tw-w)/2,(th-h)/2,(tw+w)/2,(th+h)/2};
    }
}
